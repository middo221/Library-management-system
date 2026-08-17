from datetime import timedelta
from decimal import Decimal

import pytest
from django.utils import timezone

from domains.catalog.models import BookCopy
from domains.circulation.models import Reservation
from testing.factories import BookCopyFactory, FineFactory, LoanFactory, ReservationFactory

pytestmark = pytest.mark.django_db

LOANS = "/api/v1/loans"
RESERVATIONS = "/api/v1/reservations"
FINES = "/api/v1/fines"
DASHBOARD = "/api/v1/dashboard/stats"


class TestCheckoutEndpoint:
    def test_librarian_checks_a_copy_out(self, librarian_api, member, copy):
        response = librarian_api.post(
            LOANS, {"barcode": copy.barcode, "member_id": member.id}, format="json"
        )

        assert response.status_code == 201
        assert response.data["copy"]["barcode"] == copy.barcode
        assert response.data["member"]["membership_number"] == (
            member.member_profile.membership_number
        )
        assert response.data["book"]["title"] == copy.book.title

    def test_member_cannot_check_out(self, member_api, member, copy):
        response = member_api.post(
            LOANS, {"barcode": copy.barcode, "member_id": member.id}, format="json"
        )

        assert response.status_code == 403

    def test_anonymous_is_401(self, api, member, copy):
        response = api.post(LOANS, {"barcode": copy.barcode, "member_id": member.id}, format="json")

        assert response.status_code == 401

    def test_unknown_member_is_a_field_error(self, librarian_api, copy):
        response = librarian_api.post(
            LOANS, {"barcode": copy.barcode, "member_id": 9999}, format="json"
        )

        assert response.status_code == 400
        assert response.data["error"]["details"]["member_id"] == "Unknown member."

    def test_loan_cap_surfaces_the_domain_code(self, librarian_api, member, copy, settings):
        settings.CIRCULATION = {**settings.CIRCULATION, "MAX_ACTIVE_LOANS": 1}
        LoanFactory(member=member)

        response = librarian_api.post(
            LOANS, {"barcode": copy.barcode, "member_id": member.id}, format="json"
        )

        assert response.status_code == 409
        assert response.data["error"]["code"] == "LOAN_LIMIT_REACHED"
        assert response.data["error"]["details"]["limit"] == 1


class TestLoanVisibility:
    def test_a_member_reads_their_own_loan(self, member_api, member, copy):
        loan = LoanFactory(copy=copy, member=member)

        assert member_api.get(f"{LOANS}/{loan.id}").status_code == 200

    def test_a_member_cannot_read_another_members_loan(self, other_member_api, member, copy):
        loan = LoanFactory(copy=copy, member=member)

        response = other_member_api.get(f"{LOANS}/{loan.id}")

        assert response.status_code == 403
        assert response.data["error"]["code"] == "PERMISSION_DENIED"

    def test_a_librarian_reads_any_loan(self, librarian_api, member, copy):
        loan = LoanFactory(copy=copy, member=member)

        assert librarian_api.get(f"{LOANS}/{loan.id}").status_code == 200

    def test_members_cannot_list_all_loans(self, member_api):
        assert member_api.get(LOANS).status_code == 403

    def test_my_loans_only_returns_my_loans(self, member_api, member, other_member, copy):
        LoanFactory(copy=copy, member=member)
        LoanFactory(member=other_member)

        response = member_api.get("/api/v1/members/me/loans")

        assert response.data["count"] == 1

    def test_overdue_filter(self, librarian_api, member, copy):
        LoanFactory(copy=copy, member=member, due_on=timezone.localdate() - timedelta(days=3))
        LoanFactory(member=member)

        response = librarian_api.get(LOANS, {"status": "overdue"})

        assert response.data["count"] == 1
        assert response.data["results"][0]["days_overdue"] == 3


class TestReturnEndpoint:
    def test_return_reports_what_to_do_with_the_copy(self, librarian_api, member, copy):
        loan = LoanFactory(copy=copy, member=member)
        copy.status = BookCopy.Status.ON_LOAN
        copy.save()

        response = librarian_api.post(f"{LOANS}/{loan.id}/return")

        assert response.status_code == 200
        assert response.data["copy_status"] == "AVAILABLE"
        assert response.data["message"] == "Shelve it."
        assert response.data["fine"] is None

    def test_return_of_an_overdue_loan_reports_the_fine(self, librarian_api, overdue_loan):
        response = librarian_api.post(f"{LOANS}/{overdue_loan.id}/return")

        assert response.data["fine"]["amount"] == "3.50"
        assert "fine of 3.50" in response.data["message"]

    def test_return_with_a_queue_reports_the_hold(self, librarian_api, member, other_member, copy):
        loan = LoanFactory(copy=copy, member=member)
        copy.status = BookCopy.Status.ON_LOAN
        copy.save()
        ReservationFactory(book=copy.book, member=other_member)

        response = librarian_api.post(f"{LOANS}/{loan.id}/return")

        assert response.data["copy_status"] == "RESERVED"
        assert response.data["hold"]["member"]["id"] == other_member.id
        assert "Hold this copy" in response.data["message"]

    def test_members_cannot_check_in(self, member_api, member, copy):
        loan = LoanFactory(copy=copy, member=member)

        assert member_api.post(f"{LOANS}/{loan.id}/return").status_code == 403


class TestRenewEndpoint:
    def test_a_member_renews_their_own_loan(self, member_api, member, copy):
        loan = LoanFactory(copy=copy, member=member)

        response = member_api.post(f"{LOANS}/{loan.id}/renew")

        assert response.status_code == 200
        assert response.data["renewal_count"] == 1

    def test_a_member_cannot_renew_someone_elses_loan(self, other_member_api, member, copy):
        loan = LoanFactory(copy=copy, member=member)

        assert other_member_api.post(f"{LOANS}/{loan.id}/renew").status_code == 403

    def test_blocked_renewal_explains_why(self, member_api, member, other_member, copy):
        loan = LoanFactory(copy=copy, member=member)
        ReservationFactory(book=copy.book, member=other_member)

        response = member_api.post(f"{LOANS}/{loan.id}/renew")

        assert response.status_code == 409
        assert response.data["error"]["code"] == "RENEWAL_BLOCKED_RESERVED"


class TestReservationEndpoints:
    def test_a_member_reserves_a_title(self, member_api, book):
        BookCopyFactory(book=book, status=BookCopy.Status.ON_LOAN)

        response = member_api.post(RESERVATIONS, {"book_id": book.id}, format="json")

        assert response.status_code == 201
        assert response.data["status"] == "PENDING"
        assert response.data["queue_position"] == 1

    def test_a_member_only_sees_their_own_reservations(
        self, member_api, member, other_member, book
    ):
        ReservationFactory(book=book, member=member)
        ReservationFactory(book=book, member=other_member)

        response = member_api.get(RESERVATIONS)

        assert response.data["count"] == 1

    def test_a_member_cannot_reserve_for_someone_else(self, member_api, other_member, book):
        response = member_api.post(
            RESERVATIONS, {"book_id": book.id, "member_id": other_member.id}, format="json"
        )

        assert response.status_code == 403

    def test_a_librarian_may_reserve_on_a_members_behalf(self, librarian_api, member, book):
        BookCopyFactory(book=book, status=BookCopy.Status.ON_LOAN)

        response = librarian_api.post(
            RESERVATIONS, {"book_id": book.id, "member_id": member.id}, format="json"
        )

        assert response.status_code == 201
        assert response.data["member"]["id"] == member.id

    def test_unknown_book_is_404(self, member_api):
        response = member_api.post(RESERVATIONS, {"book_id": 9999}, format="json")

        assert response.status_code == 404

    def test_cancel_is_allowed_for_the_owner(self, member_api, member, book):
        reservation = ReservationFactory(book=book, member=member)

        response = member_api.post(f"{RESERVATIONS}/{reservation.id}/cancel")

        assert response.status_code == 200
        assert response.data["status"] == "CANCELLED"

    def test_cancel_is_refused_for_another_member(self, other_member_api, member, book):
        reservation = ReservationFactory(book=book, member=member)

        assert other_member_api.post(f"{RESERVATIONS}/{reservation.id}/cancel").status_code == 403

    def test_fulfil_is_librarian_only(self, member_api, member, copy):
        reservation = ReservationFactory(
            book=copy.book, member=member, status=Reservation.Status.READY, held_copy=copy
        )

        assert member_api.post(f"{RESERVATIONS}/{reservation.id}/fulfil").status_code == 403


class TestFullReserveFulfilReturnLoop:
    """The exit criterion from Phase 6, exercised end to end through the API."""

    def test_reserve_fulfil_return_promotes_the_next_member(
        self, member_api, librarian_api, member, other_member, copy
    ):
        reserved = member_api.post(RESERVATIONS, {"book_id": copy.book_id}, format="json")
        assert reserved.data["status"] == "READY"

        queued = ReservationFactory(book=copy.book, member=other_member)

        fulfilled = librarian_api.post(f"{RESERVATIONS}/{reserved.data['id']}/fulfil")
        assert fulfilled.status_code == 201
        loan_id = fulfilled.data["id"]

        returned = librarian_api.post(f"{LOANS}/{loan_id}/return")
        assert returned.status_code == 200
        assert returned.data["copy_status"] == "RESERVED"

        queued.refresh_from_db()
        assert queued.status == Reservation.Status.READY


class TestFineEndpoints:
    def test_librarian_lists_outstanding_fines(self, librarian_api, member):
        FineFactory(loan=LoanFactory(member=member), member=member, amount=Decimal("4.00"))

        response = librarian_api.get(FINES, {"status": "outstanding"})

        assert response.data["count"] == 1
        assert response.data["results"][0]["status"] == "OUTSTANDING"

    def test_members_cannot_list_all_fines(self, member_api):
        assert member_api.get(FINES).status_code == 403

    def test_members_see_their_own_fines(self, member_api, member):
        FineFactory(loan=LoanFactory(member=member), member=member)

        response = member_api.get("/api/v1/members/me/fines")

        assert response.data["count"] == 1

    def test_pay(self, librarian_api, member):
        fine = FineFactory(loan=LoanFactory(member=member), member=member)

        response = librarian_api.post(f"{FINES}/{fine.id}/pay")

        assert response.status_code == 200
        assert response.data["status"] == "PAID"

    def test_waive_requires_a_reason(self, librarian_api, member):
        fine = FineFactory(loan=LoanFactory(member=member), member=member)

        response = librarian_api.post(f"{FINES}/{fine.id}/waive", {"reason": ""}, format="json")

        assert response.status_code == 400
        assert "reason" in response.data["error"]["details"]

    def test_waive_with_a_reason(self, librarian_api, member):
        fine = FineFactory(loan=LoanFactory(member=member), member=member)

        response = librarian_api.post(
            f"{FINES}/{fine.id}/waive", {"reason": "Goodwill"}, format="json"
        )

        assert response.status_code == 200
        assert response.data["waiver_reason"] == "Goodwill"


class TestDashboard:
    def test_librarian_sees_the_stats(self, librarian_api, member, copy):
        LoanFactory(copy=copy, member=member, due_on=timezone.localdate() - timedelta(days=2))

        response = librarian_api.get(DASHBOARD)

        assert response.status_code == 200
        assert response.data["loans_active"] == 1
        assert response.data["loans_overdue"] == 1
        assert response.data["total_titles"] == 1

    def test_members_cannot_see_the_dashboard(self, member_api):
        assert member_api.get(DASHBOARD).status_code == 403
