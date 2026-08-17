from datetime import timedelta
from decimal import Decimal

import pytest
from django.utils import timezone

from domains.catalog.models import BookCopy
from domains.circulation import services
from domains.circulation.exceptions import (
    LoanAlreadyReturned,
    RenewalBlockedOverdue,
    RenewalBlockedReserved,
    RenewalLimitReached,
)
from domains.circulation.models import Fine, Reservation
from testing.factories import BookCopyFactory, LoanFactory, ReservationFactory

pytestmark = pytest.mark.django_db


class TestReturn:
    def test_return_marks_the_loan_and_shelves_the_copy(self, member, librarian, copy):
        loan = LoanFactory(copy=copy, member=member)
        copy.status = BookCopy.Status.ON_LOAN
        copy.save()

        result = services.return_loan(loan=loan, librarian=librarian)
        copy.refresh_from_db()

        assert result["loan"].returned_at is not None
        assert result["fine"] is None
        assert copy.status == BookCopy.Status.AVAILABLE
        assert loan.checked_in_by == librarian

    def test_returning_twice_is_refused(self, librarian, overdue_loan):
        services.return_loan(loan=overdue_loan, librarian=librarian)

        with pytest.raises(LoanAlreadyReturned):
            services.return_loan(loan=overdue_loan, librarian=librarian)

    def test_overdue_return_assesses_the_right_fine(self, librarian, overdue_loan, settings):
        settings.CIRCULATION = {
            **settings.CIRCULATION,
            "OVERDUE_FINE_PER_DAY": Decimal("0.50"),
            "DEFAULT_REPLACEMENT_COST": Decimal("30.00"),
        }

        result = services.return_loan(loan=overdue_loan, librarian=librarian)

        # Seven days late at 0.50/day.
        assert result["fine"].amount == Decimal("3.50")
        assert result["fine"].reason == Fine.Reason.OVERDUE
        assert result["fine"].member == overdue_loan.member

    def test_the_fine_is_capped_at_the_replacement_cost(self, member, librarian, book, settings):
        settings.CIRCULATION = {**settings.CIRCULATION, "OVERDUE_FINE_PER_DAY": Decimal("0.50")}
        copy = BookCopyFactory(
            book=book, status=BookCopy.Status.ON_LOAN, replacement_cost=Decimal("12.00")
        )
        loan = LoanFactory(
            copy=copy, member=member, due_on=timezone.localdate() - timedelta(days=400)
        )

        result = services.return_loan(loan=loan, librarian=librarian)

        assert result["fine"].amount == Decimal("12.00")

    def test_a_loan_returned_on_time_produces_no_fine(self, member, librarian, copy):
        loan = LoanFactory(copy=copy, member=member, due_on=timezone.localdate())

        assert services.return_loan(loan=loan, librarian=librarian)["fine"] is None

    def test_a_waiting_reservation_takes_the_copy(self, member, other_member, librarian, copy):
        loan = LoanFactory(copy=copy, member=member)
        copy.status = BookCopy.Status.ON_LOAN
        copy.save()
        reservation = ReservationFactory(book=copy.book, member=other_member)

        result = services.return_loan(loan=loan, librarian=librarian)
        copy.refresh_from_db()
        reservation.refresh_from_db()

        assert copy.status == BookCopy.Status.RESERVED
        assert reservation.status == Reservation.Status.READY
        assert reservation.held_copy == copy
        assert reservation.expires_on == timezone.localdate() + timedelta(days=3)
        assert result["reservation"] == reservation

    def test_the_oldest_reservation_is_served_first(self, member, librarian, copy):
        from testing.factories import MemberFactory

        first_in_queue = MemberFactory()
        second_in_queue = MemberFactory()
        older = ReservationFactory(
            book=copy.book,
            member=first_in_queue,
            reserved_at=timezone.now() - timedelta(days=2),
        )
        ReservationFactory(book=copy.book, member=second_in_queue)

        loan = LoanFactory(copy=copy, member=member)
        copy.status = BookCopy.Status.ON_LOAN
        copy.save()

        result = services.return_loan(loan=loan, librarian=librarian)

        assert result["reservation"] == older


class TestRenew:
    def test_renewal_extends_the_due_date_and_counts(self, member, copy, librarian, settings):
        settings.CIRCULATION = {**settings.CIRCULATION, "LOAN_PERIOD_DAYS": 14}
        loan = LoanFactory(
            copy=copy, member=member, due_on=timezone.localdate() + timedelta(days=2)
        )

        services.renew_loan(loan=loan, actor=member)

        assert loan.renewal_count == 1
        assert loan.due_on == timezone.localdate() + timedelta(days=16)

    def test_renewal_cap_is_enforced(self, member, copy, settings):
        settings.CIRCULATION = {**settings.CIRCULATION, "MAX_RENEWALS": 2}
        loan = LoanFactory(copy=copy, member=member, renewal_count=2)

        with pytest.raises(RenewalLimitReached):
            services.renew_loan(loan=loan, actor=member)

    def test_overdue_loans_cannot_be_renewed(self, member, overdue_loan):
        with pytest.raises(RenewalBlockedOverdue) as exc:
            services.renew_loan(loan=overdue_loan, actor=member)

        assert exc.value.details["days_overdue"] == 7

    def test_renewal_is_refused_when_someone_is_waiting(self, member, other_member, copy):
        loan = LoanFactory(copy=copy, member=member)
        ReservationFactory(book=copy.book, member=other_member)

        with pytest.raises(RenewalBlockedReserved):
            services.renew_loan(loan=loan, actor=member)

    def test_a_cancelled_reservation_does_not_block_renewal(self, member, other_member, copy):
        loan = LoanFactory(copy=copy, member=member)
        ReservationFactory(book=copy.book, member=other_member, status=Reservation.Status.CANCELLED)

        assert services.renew_loan(loan=loan, actor=member).renewal_count == 1

    def test_a_returned_loan_cannot_be_renewed(self, member, copy, librarian):
        loan = LoanFactory(copy=copy, member=member)
        services.return_loan(loan=loan, librarian=librarian)

        with pytest.raises(LoanAlreadyReturned):
            services.renew_loan(loan=loan, actor=member)
