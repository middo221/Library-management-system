"""The awkward corners of ``circulation/services.py``.

The happy paths are covered in the other modules; these are the branches that only fire
when the world is already in an odd state — which is exactly when a library needs the code
to behave.
"""

from datetime import timedelta
from decimal import Decimal

import pytest
from django.utils import timezone

from domains.catalog.models import BookCopy
from domains.circulation import services
from domains.circulation.exceptions import (
    CopyNotAvailable,
    FineAlreadySettled,
    ReservationNotActive,
    ReservationNotReady,
)
from domains.circulation.models import Fine, Loan, Reservation
from domains.common.exceptions import ValidationError
from testing.factories import BookCopyFactory, FineFactory, LoanFactory, MemberFactory, UserFactory

pytestmark = pytest.mark.django_db


class TestEligibilityEdges:
    def test_a_user_with_no_member_profile_cannot_borrow(self, librarian, copy):
        stranger = UserFactory()

        with pytest.raises(ValidationError):
            services.checkout(barcode=copy.barcode, member=stranger, librarian=librarian)

    def test_a_librarian_account_is_not_a_borrower(self, librarian, copy):
        with pytest.raises(ValidationError):
            services.assert_member_can_borrow(librarian)


class TestCheckoutEdges:
    def test_a_stale_available_flag_still_loses_to_the_live_loan(
        self, member, other_member, librarian, copy
    ):
        """The shelf says AVAILABLE but a loan row says otherwise — the loan wins."""
        LoanFactory(copy=copy, member=other_member)
        copy.status = BookCopy.Status.AVAILABLE
        copy.save(update_fields=["status"])

        with pytest.raises(CopyNotAvailable) as exc:
            services.checkout(barcode=copy.barcode, member=member, librarian=librarian)

        assert exc.value.details["barcode"] == copy.barcode

    def test_a_reserved_copy_with_no_live_hold_can_still_be_lent(self, member, librarian, copy):
        copy.status = BookCopy.Status.RESERVED
        copy.save(update_fields=["status"])

        loan = services.checkout(barcode=copy.barcode, member=member, librarian=librarian)

        assert loan.copy == copy


class TestReturnEdges:
    def test_an_existing_fine_is_not_duplicated_on_return(self, librarian, overdue_loan):
        existing = FineFactory(
            loan=overdue_loan, member=overdue_loan.member, amount=Decimal("1.00")
        )

        result = services.return_loan(loan=overdue_loan, librarian=librarian)

        assert result["fine"] == existing
        assert Fine.objects.filter(loan=overdue_loan).count() == 1


class TestReleaseEdges:
    def test_cancelling_a_pending_reservation_touches_no_copy(self, member, book):
        BookCopyFactory(book=book, status=BookCopy.Status.ON_LOAN)
        reservation = services.reserve(book=book, member=member)

        services.cancel_reservation(reservation=reservation, actor=member)

        assert reservation.held_copy_id is None

    def test_a_ready_hold_with_no_held_copy_expires_without_error(self, member, book):
        """Data drift: a READY row that never got a copy attached must still expire cleanly."""
        Reservation.objects.create(
            book=book,
            member=member,
            status=Reservation.Status.READY,
            expires_on=timezone.localdate() - timedelta(days=1),
        )

        assert services.expire_stale_reservations() == 1

    def test_releasing_a_copy_that_moved_on_is_a_no_op(self, member, copy):
        reservation = services.reserve(book=copy.book, member=member)

        # A librarian pulls the copy off the hold shelf as damaged before the member arrives.
        copy.status = BookCopy.Status.DAMAGED
        copy.save(update_fields=["status"])

        services.cancel_reservation(reservation=reservation, actor=member)
        copy.refresh_from_db()

        assert copy.status == BookCopy.Status.DAMAGED


class TestFulfilEdges:
    def test_an_inactive_reservation_cannot_be_fulfilled(self, member, librarian, book):
        reservation = Reservation.objects.create(
            book=book, member=member, status=Reservation.Status.CANCELLED
        )

        with pytest.raises(ReservationNotActive):
            services.fulfil_reservation(reservation=reservation, librarian=librarian)

    def test_a_ready_hold_whose_copy_left_the_shelf_is_refused(self, member, librarian, copy):
        reservation = services.reserve(book=copy.book, member=member)
        copy.status = BookCopy.Status.LOST
        copy.save(update_fields=["status"])

        with pytest.raises(ReservationNotReady):
            services.fulfil_reservation(reservation=reservation, librarian=librarian)

    def test_a_pending_hold_is_fulfilled_from_any_free_copy(self, member, librarian, book):
        out = BookCopyFactory(book=book, status=BookCopy.Status.ON_LOAN)
        LoanFactory(copy=out, member=MemberFactory())
        reservation = services.reserve(book=book, member=member)
        assert reservation.status == Reservation.Status.PENDING

        # A copy comes back from the bindery and goes straight onto the shelf.
        spare = BookCopyFactory(book=book, status=BookCopy.Status.AVAILABLE)

        loan = services.fulfil_reservation(reservation=reservation, librarian=librarian)
        reservation.refresh_from_db()

        assert loan.copy == spare
        assert reservation.status == Reservation.Status.FULFILLED
        assert reservation.held_copy == spare


class TestFineEdges:
    def test_a_waived_fine_cannot_be_paid(self, librarian, member):
        fine = FineFactory(loan=LoanFactory(member=member), member=member)
        services.waive_fine(fine=fine, librarian=librarian, reason="Goodwill")

        with pytest.raises(FineAlreadySettled) as exc:
            services.pay_fine(fine=fine, librarian=librarian)

        assert exc.value.details["status"] == "WAIVED"

    def test_a_paid_fine_cannot_be_waived(self, librarian, member):
        fine = FineFactory(loan=LoanFactory(member=member), member=member)
        services.pay_fine(fine=fine, librarian=librarian)

        with pytest.raises(FineAlreadySettled):
            services.waive_fine(fine=fine, librarian=librarian, reason="Goodwill")

    def test_damage_can_be_charged_by_hand(self, librarian, member, copy):
        loan = LoanFactory(copy=copy, member=member)

        fine = services.assess_manual_fine(
            loan=loan, amount=Decimal("14.005"), reason=Fine.Reason.DAMAGE, librarian=librarian
        )

        assert fine.amount == Decimal("14.01")
        assert fine.reason == Fine.Reason.DAMAGE
        assert fine.member == member

    def test_only_one_fine_per_loan(self, librarian, member, copy):
        loan = LoanFactory(copy=copy, member=member)
        services.assess_manual_fine(
            loan=loan, amount=Decimal("5.00"), reason=Fine.Reason.DAMAGE, librarian=librarian
        )
        loan.refresh_from_db()

        with pytest.raises(FineAlreadySettled):
            services.assess_manual_fine(
                loan=loan, amount=Decimal("5.00"), reason=Fine.Reason.LOST, librarian=librarian
            )


class TestLoanModelProperties:
    def test_days_overdue_is_measured_at_the_return_date_once_returned(self, member, copy):
        loan = LoanFactory(
            copy=copy,
            member=member,
            due_on=timezone.localdate() - timedelta(days=10),
            returned_at=timezone.now() - timedelta(days=4),
        )

        assert loan.is_overdue is True
        assert loan.days_overdue == 6

    def test_a_returned_on_time_loan_is_not_overdue(self, member, copy):
        loan = LoanFactory(
            copy=copy, member=member, due_on=timezone.localdate(), returned_at=timezone.now()
        )

        assert loan.is_overdue is False
        assert loan.days_overdue == 0

    def test_queue_position_is_zero_once_a_reservation_closes(self, member, book):
        reservation = Reservation.objects.create(
            book=book, member=member, status=Reservation.Status.EXPIRED
        )

        assert reservation.queue_position == 0

    def test_loan_and_reservation_string_forms_name_the_object(self, member, copy):
        loan = LoanFactory(copy=copy, member=member)

        assert copy.barcode in str(loan)
        assert Loan.objects.filter(pk=loan.pk).exists()
