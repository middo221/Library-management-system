from django.conf import settings
from django.db import models
from django.utils import timezone

from domains.catalog.models import Book, BookCopy
from domains.common.models import TimeStampedModel


class Loan(TimeStampedModel):
    copy = models.ForeignKey(BookCopy, on_delete=models.PROTECT, related_name="loans")
    member = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="loans"
    )

    checked_out_at = models.DateTimeField(default=timezone.now)
    due_on = models.DateField(db_index=True)
    returned_at = models.DateTimeField(null=True, blank=True, db_index=True)

    renewal_count = models.PositiveSmallIntegerField(default=0)

    checked_out_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="loans_issued",
    )
    checked_in_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="loans_received",
    )

    class Meta:
        ordering = ("-checked_out_at",)
        constraints = [
            # A physical copy can be in exactly one person's hands at a time. Enforced by the
            # database, not just by the service, because concurrency is the whole risk here.
            models.UniqueConstraint(
                fields=("copy",),
                condition=models.Q(returned_at__isnull=True),
                name="unique_active_loan_per_copy",
            )
        ]
        indexes = [models.Index(fields=("member", "returned_at"))]

    def __str__(self) -> str:
        return f"{self.copy.barcode} → {self.member.email}"

    @property
    def owner_user(self):
        """Hook for ``IsOwnerOrLibrarian``."""
        return self.member

    @property
    def is_active(self) -> bool:
        return self.returned_at is None

    @property
    def is_overdue(self) -> bool:
        if self.returned_at is not None:
            return self.returned_at.date() > self.due_on
        return timezone.localdate() > self.due_on

    @property
    def days_overdue(self) -> int:
        reference = self.returned_at.date() if self.returned_at else timezone.localdate()
        return max((reference - self.due_on).days, 0)


class Reservation(TimeStampedModel):
    """Members reserve a *title*; the hold is attached to a copy only once one comes back."""

    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        READY = "READY", "Ready for collection"
        FULFILLED = "FULFILLED", "Fulfilled"
        CANCELLED = "CANCELLED", "Cancelled"
        EXPIRED = "EXPIRED", "Expired"

    #: Statuses where the member is still waiting or collecting.
    ACTIVE_STATUSES = (Status.PENDING, Status.READY)

    book = models.ForeignKey(Book, on_delete=models.CASCADE, related_name="reservations")
    member = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="reservations"
    )
    status = models.CharField(
        max_length=16, choices=Status.choices, default=Status.PENDING, db_index=True
    )

    reserved_at = models.DateTimeField(default=timezone.now, db_index=True)
    ready_at = models.DateTimeField(null=True, blank=True)
    expires_on = models.DateField(null=True, blank=True)

    #: Set when the reservation goes READY, so the hold shelf knows which copy to keep back.
    held_copy = models.ForeignKey(
        BookCopy, on_delete=models.SET_NULL, null=True, blank=True, related_name="holds"
    )

    class Meta:
        ordering = ("reserved_at",)
        constraints = [
            models.UniqueConstraint(
                fields=("book", "member"),
                condition=models.Q(status__in=("PENDING", "READY")),
                name="unique_active_reservation_per_book_member",
            )
        ]
        indexes = [models.Index(fields=("book", "status", "reserved_at"))]

    def __str__(self) -> str:
        return f"{self.book.title} → {self.member.email} ({self.status})"

    @property
    def owner_user(self):
        return self.member

    @property
    def is_active(self) -> bool:
        return self.status in self.ACTIVE_STATUSES

    @property
    def queue_position(self) -> int:
        """1-based position among active reservations for the same title, oldest first."""
        if not self.is_active:
            return 0
        return (
            Reservation.objects.filter(
                book_id=self.book_id,
                status__in=self.ACTIVE_STATUSES,
                reserved_at__lt=self.reserved_at,
            ).count()
            + 1
        )


class Fine(TimeStampedModel):
    class Reason(models.TextChoices):
        OVERDUE = "OVERDUE", "Overdue"
        DAMAGE = "DAMAGE", "Damage"
        LOST = "LOST", "Lost"

    loan = models.OneToOneField(Loan, on_delete=models.CASCADE, related_name="fine")
    member = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="fines"
    )

    amount = models.DecimalField(max_digits=8, decimal_places=2)
    reason = models.CharField(max_length=16, choices=Reason.choices, default=Reason.OVERDUE)

    assessed_on = models.DateField(default=timezone.localdate)
    paid_at = models.DateTimeField(null=True, blank=True)
    waived_at = models.DateTimeField(null=True, blank=True)
    waived_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="fines_waived",
    )
    waiver_reason = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ("-assessed_on", "-id")
        indexes = [models.Index(fields=("member", "paid_at", "waived_at"))]

    def __str__(self) -> str:
        return f"{self.member.email} — {self.amount} ({self.reason})"

    @property
    def owner_user(self):
        return self.member

    @property
    def is_outstanding(self) -> bool:
        return self.paid_at is None and self.waived_at is None

    @property
    def status(self) -> str:
        if self.paid_at is not None:
            return "PAID"
        if self.waived_at is not None:
            return "WAIVED"
        return "OUTSTANDING"


#: Module-level aliases for ``SPECTACULAR_SETTINGS["ENUM_NAME_OVERRIDES"]``.
RESERVATION_STATUS_CHOICES = Reservation.Status.choices
FINE_REASON_CHOICES = Fine.Reason.choices
