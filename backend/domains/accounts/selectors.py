"""Read queries for accounts."""

from decimal import Decimal

from django.db.models import Count, DecimalField, OuterRef, Q, QuerySet, Subquery, Sum, Value
from django.db.models.functions import Coalesce

from domains.accounts.models import User


def members_queryset(*, search: str = "", is_suspended: bool | None = None) -> QuerySet[User]:
    """Members with their live borrowing summary, annotated in one round trip."""
    from domains.circulation.models import Fine

    unpaid_totals = (
        Fine.objects.filter(member=OuterRef("pk"), paid_at__isnull=True, waived_at__isnull=True)
        .values("member")
        .annotate(total=Sum("amount"))
        .values("total")[:1]
    )

    queryset = (
        User.objects.filter(role=User.Role.MEMBER)
        .select_related("member_profile")
        .annotate(
            active_loan_count=Count(
                "loans", filter=Q(loans__returned_at__isnull=True), distinct=True
            ),
            unpaid_fine_total=Coalesce(
                Subquery(unpaid_totals, output_field=DecimalField(max_digits=8, decimal_places=2)),
                Value(Decimal("0.00"), output_field=DecimalField(max_digits=8, decimal_places=2)),
            ),
        )
    )

    if search:
        queryset = queryset.filter(
            Q(email__icontains=search)
            | Q(first_name__icontains=search)
            | Q(last_name__icontains=search)
            | Q(member_profile__membership_number__icontains=search)
        )

    if is_suspended is not None:
        queryset = queryset.filter(member_profile__is_suspended=is_suspended)

    return queryset.order_by("member_profile__membership_number")


def get_member(*, member_id: int) -> User | None:
    return (
        User.objects.filter(pk=member_id, role=User.Role.MEMBER)
        .select_related("member_profile")
        .first()
    )
