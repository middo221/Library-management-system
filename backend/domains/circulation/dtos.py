"""Circulation DTOs.

Loan and reservation responses carry enough denormalised context (title, barcode, call
number, membership number) that the UI never needs a second request to render a row.
"""

from rest_framework import serializers

from domains.circulation.models import Fine, Reservation

# --------------------------------------------------------------------------------------
# Shared fragments
# --------------------------------------------------------------------------------------


class MemberSummaryResponse(serializers.Serializer):
    id = serializers.IntegerField()
    email = serializers.EmailField()
    full_name = serializers.CharField()
    membership_number = serializers.CharField(source="member_profile.membership_number", default="")


class CopySummaryResponse(serializers.Serializer):
    id = serializers.IntegerField()
    barcode = serializers.CharField()
    call_number = serializers.CharField()
    status = serializers.CharField()


class BookSummaryResponse(serializers.Serializer):
    id = serializers.IntegerField()
    title = serializers.CharField()
    isbn = serializers.CharField()
    cover_url = serializers.CharField()
    authors = serializers.SerializerMethodField()

    def get_authors(self, obj) -> list[str]:
        return [author.name for author in obj.authors.all()]


# --------------------------------------------------------------------------------------
# Loans
# --------------------------------------------------------------------------------------


class LoanResponse(serializers.Serializer):
    id = serializers.IntegerField()
    book = BookSummaryResponse(source="copy.book")
    copy = CopySummaryResponse()
    member = MemberSummaryResponse()
    checked_out_at = serializers.DateTimeField()
    due_on = serializers.DateField()
    returned_at = serializers.DateTimeField(allow_null=True)
    renewal_count = serializers.IntegerField()
    is_active = serializers.BooleanField()
    is_overdue = serializers.BooleanField()
    days_overdue = serializers.IntegerField()


class CheckoutRequest(serializers.Serializer):
    barcode = serializers.CharField(max_length=32)
    member_id = serializers.IntegerField()

    def validate_barcode(self, value: str) -> str:
        return value.strip()


class RenewRequest(serializers.Serializer):
    """Renewal takes no body; declared so the schema is explicit rather than absent."""


class ReturnResponse(serializers.Serializer):
    loan = LoanResponse()
    fine = serializers.SerializerMethodField()
    hold = serializers.SerializerMethodField()
    copy_status = serializers.CharField(source="copy.status")
    message = serializers.SerializerMethodField()

    def get_fine(self, obj) -> dict | None:
        return FineResponse(obj["fine"]).data if obj["fine"] else None

    def get_hold(self, obj) -> dict | None:
        return ReservationResponse(obj["reservation"]).data if obj["reservation"] else None

    def get_message(self, obj) -> str:
        if obj["reservation"]:
            member = obj["reservation"].member
            return f"Hold this copy for {member.full_name}."
        if obj["fine"]:
            return f"Overdue — a fine of {obj['fine'].amount} has been assessed."
        return "Shelve it."


# --------------------------------------------------------------------------------------
# Reservations
# --------------------------------------------------------------------------------------


class ReservationResponse(serializers.Serializer):
    id = serializers.IntegerField()
    book = BookSummaryResponse()
    member = MemberSummaryResponse()
    status = serializers.ChoiceField(choices=Reservation.Status.choices)
    reserved_at = serializers.DateTimeField()
    ready_at = serializers.DateTimeField(allow_null=True)
    expires_on = serializers.DateField(allow_null=True)
    queue_position = serializers.IntegerField()
    held_copy = CopySummaryResponse(allow_null=True)


class ReservationCreateRequest(serializers.Serializer):
    book_id = serializers.IntegerField()
    #: Librarians may place a reservation on a member's behalf at the desk.
    member_id = serializers.IntegerField(required=False)


class CancelReservationRequest(serializers.Serializer):
    """No body required."""


# --------------------------------------------------------------------------------------
# Fines
# --------------------------------------------------------------------------------------


class FineResponse(serializers.Serializer):
    id = serializers.IntegerField()
    loan_id = serializers.IntegerField()
    member = MemberSummaryResponse()
    book_title = serializers.CharField(source="loan.copy.book.title", read_only=True)
    amount = serializers.DecimalField(max_digits=8, decimal_places=2)
    reason = serializers.ChoiceField(choices=Fine.Reason.choices)
    status = serializers.CharField()
    assessed_on = serializers.DateField()
    paid_at = serializers.DateTimeField(allow_null=True)
    waived_at = serializers.DateTimeField(allow_null=True)
    waiver_reason = serializers.CharField()


class WaiveFineRequest(serializers.Serializer):
    reason = serializers.CharField(max_length=255)

    def validate_reason(self, value: str) -> str:
        if not value.strip():
            raise serializers.ValidationError("A reason is required to waive a fine.")
        return value.strip()


class PayFineRequest(serializers.Serializer):
    """No body required."""


# --------------------------------------------------------------------------------------
# Dashboard
# --------------------------------------------------------------------------------------


class DashboardStatsResponse(serializers.Serializer):
    total_titles = serializers.IntegerField()
    total_copies = serializers.IntegerField()
    copies_available = serializers.IntegerField()
    copies_on_loan = serializers.IntegerField()
    loans_active = serializers.IntegerField()
    loans_overdue = serializers.IntegerField()
    loans_due_today = serializers.IntegerField()
    active_members = serializers.IntegerField()
    suspended_members = serializers.IntegerField()
    reservations_waiting = serializers.IntegerField()
    reservations_ready = serializers.IntegerField()
    unpaid_fines_total = serializers.DecimalField(max_digits=10, decimal_places=2)
    unpaid_fines_count = serializers.IntegerField()
