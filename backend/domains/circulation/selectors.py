"""Circulation read queries, including the librarian dashboard."""

from decimal import Decimal

from django.db.models import Count, Q, QuerySet, Sum
from django.utils import timezone

from domains.accounts.models import MemberProfile, User
from domains.catalog.models import Book, BookCopy
from domains.circulation.models import Fine, Loan, Reservation

_LOAN_RELATED = ("copy", "copy__book", "member", "member__member_profile", "checked_out_by")


def list_loans(
    *,
    status: str = "",
    member: int | None = None,
    book: int | None = None,
    search: str = "",
) -> QuerySet[Loan]:
    queryset = Loan.objects.select_related(*_LOAN_RELATED).prefetch_related("copy__book__authors")

    today = timezone.localdate()
    if status == "active":
        queryset = queryset.filter(returned_at__isnull=True)
    elif status == "overdue":
        queryset = queryset.filter(returned_at__isnull=True, due_on__lt=today)
    elif status == "returned":
        queryset = queryset.filter(returned_at__isnull=False)

    if member is not None:
        queryset = queryset.filter(member_id=member)
    if book is not None:
        queryset = queryset.filter(copy__book_id=book)
    if search:
        queryset = queryset.filter(
            Q(copy__barcode__icontains=search)
            | Q(copy__book__title__icontains=search)
            | Q(member__email__icontains=search)
            | Q(member__member_profile__membership_number__icontains=search)
        )

    return queryset.order_by("returned_at", "due_on", "-checked_out_at")


def get_loan(*, loan_id: int) -> Loan | None:
    return Loan.objects.select_related(*_LOAN_RELATED).filter(pk=loan_id).first()


def list_reservations(
    *, member: int | None = None, book: int | None = None, status: str = ""
) -> QuerySet[Reservation]:
    queryset = Reservation.objects.select_related(
        "book", "member", "member__member_profile", "held_copy"
    ).prefetch_related("book__authors")

    if member is not None:
        queryset = queryset.filter(member_id=member)
    if book is not None:
        queryset = queryset.filter(book_id=book)
    if status == "active":
        queryset = queryset.filter(status__in=Reservation.ACTIVE_STATUSES)
    elif status:
        queryset = queryset.filter(status=status)

    return queryset.order_by("reserved_at")


def get_reservation(*, reservation_id: int) -> Reservation | None:
    return (
        Reservation.objects.select_related("book", "member", "held_copy")
        .filter(pk=reservation_id)
        .first()
    )


def list_fines(*, member: int | None = None, status: str = "") -> QuerySet[Fine]:
    queryset = Fine.objects.select_related(
        "member", "member__member_profile", "loan", "loan__copy", "loan__copy__book"
    )

    if member is not None:
        queryset = queryset.filter(member_id=member)
    if status == "outstanding":
        queryset = queryset.filter(paid_at__isnull=True, waived_at__isnull=True)
    elif status == "paid":
        queryset = queryset.filter(paid_at__isnull=False)
    elif status == "waived":
        queryset = queryset.filter(waived_at__isnull=False)

    return queryset.order_by("-assessed_on", "-id")


def get_fine(*, fine_id: int) -> Fine | None:
    return (
        Fine.objects.select_related("member", "loan", "loan__copy", "loan__copy__book")
        .filter(pk=fine_id)
        .first()
    )


def dashboard_stats() -> dict:
    today = timezone.localdate()

    copy_counts = BookCopy.objects.aggregate(
        total=Count("id"),
        on_loan=Count("id", filter=Q(status=BookCopy.Status.ON_LOAN)),
        available=Count("id", filter=Q(status=BookCopy.Status.AVAILABLE)),
    )
    loan_counts = Loan.objects.aggregate(
        active=Count("id", filter=Q(returned_at__isnull=True)),
        overdue=Count("id", filter=Q(returned_at__isnull=True, due_on__lt=today)),
        due_today=Count("id", filter=Q(returned_at__isnull=True, due_on=today)),
    )
    reservation_counts = Reservation.objects.aggregate(
        pending=Count("id", filter=Q(status=Reservation.Status.PENDING)),
        ready=Count("id", filter=Q(status=Reservation.Status.READY)),
    )
    fines = Fine.objects.filter(paid_at__isnull=True, waived_at__isnull=True).aggregate(
        total=Sum("amount"), count=Count("id")
    )

    return {
        "total_titles": Book.objects.count(),
        "total_copies": copy_counts["total"],
        "copies_available": copy_counts["available"],
        "copies_on_loan": copy_counts["on_loan"],
        "loans_active": loan_counts["active"],
        "loans_overdue": loan_counts["overdue"],
        "loans_due_today": loan_counts["due_today"],
        "active_members": User.objects.filter(
            role=User.Role.MEMBER, is_active=True, member_profile__is_suspended=False
        ).count(),
        "suspended_members": MemberProfile.objects.filter(is_suspended=True).count(),
        "reservations_waiting": reservation_counts["pending"],
        "reservations_ready": reservation_counts["ready"],
        "unpaid_fines_total": Decimal(fines["total"] or 0),
        "unpaid_fines_count": fines["count"],
    }
