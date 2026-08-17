"""Checkout rules. The table in §3 of the plan is the test list."""

from datetime import timedelta
from decimal import Decimal

import pytest
from django.db import IntegrityError, transaction
from django.utils import timezone

from domains.catalog.models import BookCopy
from domains.circulation import services
from domains.circulation.exceptions import (
    CopyHeldForOtherMember,
    CopyNotAvailable,
    LoanLimitReached,
    MembershipExpired,
    MembershipSuspended,
    UnpaidFines,
)
from domains.circulation.models import Loan, Reservation
from testing.factories import BookCopyFactory, FineFactory, LoanFactory, ReservationFactory

pytestmark = pytest.mark.django_db


class TestCheckoutHappyPath:
    def test_creates_a_loan_and_marks_the_copy_on_loan(self, member, librarian, copy):
        loan = services.checkout(barcode=copy.barcode, member=member, librarian=librarian)
        copy.refresh_from_db()

        assert loan.member == member
        assert loan.checked_out_by == librarian
        assert copy.status == BookCopy.Status.ON_LOAN

    def test_due_date_is_the_configured_loan_period(self, member, librarian, copy, settings):
        settings.CIRCULATION = {**settings.CIRCULATION, "LOAN_PERIOD_DAYS": 21}

        loan = services.checkout(barcode=copy.barcode, member=member, librarian=librarian)

        assert loan.due_on == timezone.localdate() + timedelta(days=21)

    def test_barcode_whitespace_is_tolerated(self, member, librarian, copy):
        loan = services.checkout(barcode=f"  {copy.barcode} ", member=member, librarian=librarian)

        assert loan.copy == copy


class TestCheckoutBlocks:
    def test_unknown_barcode_is_a_404(self, member, librarian):
        with pytest.raises(CopyNotAvailable) as exc:
            services.checkout(barcode="NOPE", member=member, librarian=librarian)

        assert exc.value.status_code == 404

    @pytest.mark.parametrize(
        "status", [BookCopy.Status.LOST, BookCopy.Status.DAMAGED, BookCopy.Status.WITHDRAWN]
    )
    def test_copy_not_on_the_shelf_is_refused(self, member, librarian, book, status):
        copy = BookCopyFactory(book=book, status=status)

        with pytest.raises(CopyNotAvailable) as exc:
            services.checkout(barcode=copy.barcode, member=member, librarian=librarian)

        assert exc.value.code == "COPY_NOT_AVAILABLE"

    def test_loan_cap_blocks_with_its_own_code(self, member, librarian, copy, settings):
        settings.CIRCULATION = {**settings.CIRCULATION, "MAX_ACTIVE_LOANS": 2}
        LoanFactory.create_batch(2, member=member)

        with pytest.raises(LoanLimitReached) as exc:
            services.checkout(barcode=copy.barcode, member=member, librarian=librarian)

        assert exc.value.code == "LOAN_LIMIT_REACHED"
        assert exc.value.details["limit"] == 2

    def test_suspension_blocks_with_its_own_code(self, member, librarian, copy):
        member.member_profile.is_suspended = True
        member.member_profile.suspension_reason = "Unreturned items"
        member.member_profile.save()

        with pytest.raises(MembershipSuspended) as exc:
            services.checkout(barcode=copy.barcode, member=member, librarian=librarian)

        assert exc.value.code == "MEMBERSHIP_SUSPENDED"
        assert exc.value.details["reason"] == "Unreturned items"

    def test_expired_membership_blocks_with_its_own_code(self, member, librarian, copy):
        member.member_profile.membership_expires_on = timezone.localdate() - timedelta(days=1)
        member.member_profile.save()

        with pytest.raises(MembershipExpired) as exc:
            services.checkout(barcode=copy.barcode, member=member, librarian=librarian)

        assert exc.value.code == "MEMBERSHIP_EXPIRED"

    def test_unpaid_fines_over_the_threshold_block_borrowing(
        self, member, librarian, copy, settings
    ):
        settings.CIRCULATION = {
            **settings.CIRCULATION,
            "UNPAID_FINE_BLOCK_THRESHOLD": Decimal("10.00"),
        }
        FineFactory(loan=LoanFactory(member=member), member=member, amount=Decimal("12.00"))

        with pytest.raises(UnpaidFines) as exc:
            services.checkout(barcode=copy.barcode, member=member, librarian=librarian)

        assert exc.value.code == "UNPAID_FINES"

    def test_a_paid_fine_does_not_block(self, member, librarian, copy):
        FineFactory(
            loan=LoanFactory(member=member),
            member=member,
            amount=Decimal("12.00"),
            paid_at=timezone.now(),
        )

        assert services.checkout(barcode=copy.barcode, member=member, librarian=librarian)


class TestReservationInteraction:
    def test_a_copy_held_for_another_member_cannot_be_lent_out(
        self, member, other_member, librarian, copy
    ):
        ReservationFactory(
            book=copy.book,
            member=other_member,
            status=Reservation.Status.READY,
            held_copy=copy,
        )
        copy.status = BookCopy.Status.RESERVED
        copy.save()

        with pytest.raises(CopyHeldForOtherMember) as exc:
            services.checkout(barcode=copy.barcode, member=member, librarian=librarian)

        assert exc.value.code == "COPY_HELD_FOR_OTHER_MEMBER"

    def test_the_member_the_hold_belongs_to_may_take_it(self, member, librarian, copy):
        reservation = ReservationFactory(
            book=copy.book, member=member, status=Reservation.Status.READY, held_copy=copy
        )
        copy.status = BookCopy.Status.RESERVED
        copy.save()

        services.checkout(barcode=copy.barcode, member=member, librarian=librarian)
        reservation.refresh_from_db()

        assert reservation.status == Reservation.Status.FULFILLED


class TestConcurrency:
    def test_the_database_refuses_a_second_active_loan_on_one_copy(
        self, member, other_member, copy
    ):
        LoanFactory(copy=copy, member=member)

        with pytest.raises(IntegrityError), transaction.atomic():
            Loan.objects.create(
                copy=copy, member=other_member, due_on=timezone.localdate() + timedelta(days=14)
            )

    def test_the_second_checkout_of_the_same_copy_fails_cleanly(
        self, member, other_member, librarian, copy
    ):
        """Serialised by ``select_for_update`` in the service; this asserts the loser gets a
        domain error rather than a database traceback."""
        services.checkout(barcode=copy.barcode, member=member, librarian=librarian)

        with pytest.raises(CopyNotAvailable):
            services.checkout(barcode=copy.barcode, member=other_member, librarian=librarian)

        assert Loan.objects.filter(copy=copy, returned_at__isnull=True).count() == 1
