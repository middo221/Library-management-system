from datetime import timedelta
from decimal import Decimal

import pytest
from django.utils import timezone

from domains.catalog.models import BookCopy
from domains.circulation import services
from domains.circulation.exceptions import (
    AlreadyOnLoanByMember,
    DuplicateReservation,
    FineAlreadySettled,
    MembershipSuspended,
    NoCopyAvailable,
    ReservationNotActive,
)
from domains.circulation.models import Reservation
from domains.common.exceptions import ValidationError
from testing.factories import (
    BookCopyFactory,
    FineFactory,
    LoanFactory,
    MemberFactory,
)

pytestmark = pytest.mark.django_db


class TestReserve:
    def test_reserving_an_available_title_holds_a_copy_immediately(self, member, copy):
        reservation = services.reserve(book=copy.book, member=member)
        copy.refresh_from_db()

        assert reservation.status == Reservation.Status.READY
        assert reservation.held_copy == copy
        assert copy.status == BookCopy.Status.RESERVED

    def test_reserving_a_title_that_is_all_out_joins_the_queue(self, member, book):
        BookCopyFactory(book=book, status=BookCopy.Status.ON_LOAN)

        reservation = services.reserve(book=book, member=member)

        assert reservation.status == Reservation.Status.PENDING
        assert reservation.queue_position == 1

    def test_queue_positions_follow_reservation_order(self, book):
        BookCopyFactory(book=book, status=BookCopy.Status.ON_LOAN)
        first = services.reserve(book=book, member=MemberFactory())
        second = services.reserve(book=book, member=MemberFactory())

        assert first.queue_position == 1
        assert second.queue_position == 2

    def test_a_member_cannot_reserve_the_same_title_twice(self, member, book):
        BookCopyFactory(book=book, status=BookCopy.Status.ON_LOAN)
        services.reserve(book=book, member=member)

        with pytest.raises(DuplicateReservation):
            services.reserve(book=book, member=member)

    def test_a_member_holding_the_title_cannot_reserve_it(self, member, copy):
        LoanFactory(copy=copy, member=member)
        copy.status = BookCopy.Status.ON_LOAN
        copy.save()

        with pytest.raises(AlreadyOnLoanByMember):
            services.reserve(book=copy.book, member=member)

    def test_a_suspended_member_cannot_reserve(self, member, book):
        member.member_profile.is_suspended = True
        member.member_profile.save()

        with pytest.raises(MembershipSuspended):
            services.reserve(book=book, member=member)

    def test_the_loan_cap_does_not_block_queueing(self, member, book, settings):
        settings.CIRCULATION = {**settings.CIRCULATION, "MAX_ACTIVE_LOANS": 1}
        LoanFactory(member=member)
        BookCopyFactory(book=book, status=BookCopy.Status.ON_LOAN)

        assert services.reserve(book=book, member=member).status == Reservation.Status.PENDING


class TestCancel:
    def test_cancelling_a_ready_hold_offers_the_copy_to_the_next_member(self, copy):
        first = MemberFactory()
        second = MemberFactory()
        held = services.reserve(book=copy.book, member=first)
        queued = services.reserve(book=copy.book, member=second)

        services.cancel_reservation(reservation=held, actor=first)
        copy.refresh_from_db()
        queued.refresh_from_db()

        assert queued.status == Reservation.Status.READY
        assert copy.status == BookCopy.Status.RESERVED

    def test_cancelling_the_only_hold_returns_the_copy_to_the_shelf(self, member, copy):
        reservation = services.reserve(book=copy.book, member=member)

        services.cancel_reservation(reservation=reservation, actor=member)
        copy.refresh_from_db()

        assert copy.status == BookCopy.Status.AVAILABLE

    def test_an_inactive_reservation_cannot_be_cancelled_again(self, member, copy):
        reservation = services.reserve(book=copy.book, member=member)
        services.cancel_reservation(reservation=reservation, actor=member)

        with pytest.raises(ReservationNotActive):
            services.cancel_reservation(reservation=reservation, actor=member)


class TestFulfil:
    def test_a_ready_hold_becomes_a_loan(self, member, librarian, copy):
        reservation = services.reserve(book=copy.book, member=member)

        loan = services.fulfil_reservation(reservation=reservation, librarian=librarian)
        reservation.refresh_from_db()
        copy.refresh_from_db()

        assert loan.member == member
        assert loan.copy == copy
        assert reservation.status == Reservation.Status.FULFILLED
        assert copy.status == BookCopy.Status.ON_LOAN

    def test_a_pending_hold_with_nothing_on_the_shelf_cannot_be_fulfilled(
        self, member, librarian, book
    ):
        BookCopyFactory(book=book, status=BookCopy.Status.ON_LOAN)
        reservation = services.reserve(book=book, member=member)

        with pytest.raises(NoCopyAvailable):
            services.fulfil_reservation(reservation=reservation, librarian=librarian)

    def test_borrowing_rules_still_apply_at_fulfilment(self, member, librarian, copy, settings):
        settings.CIRCULATION = {**settings.CIRCULATION, "MAX_ACTIVE_LOANS": 1}
        reservation = services.reserve(book=copy.book, member=member)
        LoanFactory(member=member)

        from domains.circulation.exceptions import LoanLimitReached

        with pytest.raises(LoanLimitReached):
            services.fulfil_reservation(reservation=reservation, librarian=librarian)


class TestExpiry:
    def test_stale_ready_holds_expire_and_move_down_the_queue(self, copy):
        first = MemberFactory()
        second = MemberFactory()
        held = services.reserve(book=copy.book, member=first)
        queued = services.reserve(book=copy.book, member=second)

        held.expires_on = timezone.localdate() - timedelta(days=1)
        held.save(update_fields=["expires_on"])

        assert services.expire_stale_reservations() == 1

        held.refresh_from_db()
        queued.refresh_from_db()
        copy.refresh_from_db()

        assert held.status == Reservation.Status.EXPIRED
        assert queued.status == Reservation.Status.READY
        assert copy.status == BookCopy.Status.RESERVED

    def test_holds_within_their_shelf_time_are_left_alone(self, member, copy):
        services.reserve(book=copy.book, member=member)

        assert services.expire_stale_reservations() == 0


class TestFines:
    def test_pay_marks_the_fine_settled(self, librarian, member):
        fine = FineFactory(loan=LoanFactory(member=member), member=member)

        settled = services.pay_fine(fine=fine, librarian=librarian)

        assert settled.paid_at is not None
        assert settled.status == "PAID"

    def test_paying_twice_is_refused(self, librarian, member):
        fine = FineFactory(loan=LoanFactory(member=member), member=member)
        services.pay_fine(fine=fine, librarian=librarian)

        with pytest.raises(FineAlreadySettled):
            services.pay_fine(fine=fine, librarian=librarian)

    def test_waiving_records_who_and_why(self, librarian, member):
        fine = FineFactory(loan=LoanFactory(member=member), member=member)

        waived = services.waive_fine(fine=fine, librarian=librarian, reason="Hospital stay")

        assert waived.waived_by == librarian
        assert waived.waiver_reason == "Hospital stay"
        assert waived.status == "WAIVED"

    def test_waiving_without_a_reason_is_refused(self, librarian, member):
        fine = FineFactory(loan=LoanFactory(member=member), member=member)

        with pytest.raises(ValidationError):
            services.waive_fine(fine=fine, librarian=librarian, reason="   ")

    def test_settled_fines_stop_counting_against_the_member(self, librarian, member):
        fine = FineFactory(loan=LoanFactory(member=member), member=member, amount=Decimal("8.00"))

        assert services.outstanding_fine_total(member) == Decimal("8.00")

        services.pay_fine(fine=fine, librarian=librarian)

        assert services.outstanding_fine_total(member) == Decimal("0")
