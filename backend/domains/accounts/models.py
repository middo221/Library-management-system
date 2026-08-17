from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.db import models, transaction
from django.utils import timezone

from domains.accounts.managers import UserManager
from domains.common.models import TimeStampedModel


class User(AbstractBaseUser, PermissionsMixin):
    class Role(models.TextChoices):
        LIBRARIAN = "LIBRARIAN", "Librarian"
        MEMBER = "MEMBER", "Member"

    email = models.EmailField(unique=True, db_index=True)
    first_name = models.CharField(max_length=80, blank=True)
    last_name = models.CharField(max_length=80, blank=True)
    role = models.CharField(max_length=16, choices=Role.choices, default=Role.MEMBER, db_index=True)

    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    date_joined = models.DateTimeField(default=timezone.now)

    objects = UserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS: list[str] = []

    class Meta:
        ordering = ("last_name", "first_name", "email")
        verbose_name = "user"
        verbose_name_plural = "users"

    def __str__(self) -> str:
        return self.email

    @property
    def full_name(self) -> str:
        name = f"{self.first_name} {self.last_name}".strip()
        return name or self.email

    @property
    def is_librarian(self) -> bool:
        return self.role == self.Role.LIBRARIAN

    @property
    def is_member(self) -> bool:
        return self.role == self.Role.MEMBER


class MemberProfile(TimeStampedModel):
    """Borrowing-side attributes. Only ``MEMBER`` users have one."""

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="member_profile")
    membership_number = models.CharField(max_length=16, unique=True, db_index=True)
    phone = models.CharField(max_length=32, blank=True)
    address = models.TextField(blank=True)
    joined_on = models.DateField(default=timezone.localdate)
    membership_expires_on = models.DateField(null=True, blank=True)
    is_suspended = models.BooleanField(default=False)
    suspension_reason = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ("membership_number",)

    def __str__(self) -> str:
        return f"{self.membership_number} ({self.user.email})"

    @property
    def is_expired(self) -> bool:
        if self.membership_expires_on is None:
            return False
        return self.membership_expires_on < timezone.localdate()

    @property
    def can_borrow(self) -> bool:
        return self.user.is_active and not self.is_suspended and not self.is_expired

    @classmethod
    @transaction.atomic
    def next_membership_number(cls) -> str:
        """``M-000142``. Sequential and gap-tolerant — it is a label, not a key."""
        last = cls.objects.select_for_update().order_by("-id").first()
        next_index = 1 if last is None else last.id + 1
        return f"M-{next_index:06d}"


#: Module-level alias for ``SPECTACULAR_SETTINGS["ENUM_NAME_OVERRIDES"]``.
USER_ROLE_CHOICES = User.Role.choices
