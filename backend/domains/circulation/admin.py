from django.contrib import admin

from domains.circulation.models import Fine, Loan, Reservation


@admin.register(Loan)
class LoanAdmin(admin.ModelAdmin):
    list_display = ("copy", "member", "checked_out_at", "due_on", "returned_at")
    list_filter = ("returned_at",)
    search_fields = ("copy__barcode", "copy__book__title", "member__email")
    autocomplete_fields = ("copy", "member")


@admin.register(Reservation)
class ReservationAdmin(admin.ModelAdmin):
    list_display = ("book", "member", "status", "reserved_at", "expires_on")
    list_filter = ("status",)
    search_fields = ("book__title", "member__email")


@admin.register(Fine)
class FineAdmin(admin.ModelAdmin):
    list_display = ("member", "amount", "reason", "assessed_on", "paid_at", "waived_at")
    list_filter = ("reason", "paid_at", "waived_at")
    search_fields = ("member__email",)
