"""Request and response DTOs for accounts.

Plain ``Serializer`` throughout: the wire format is chosen here, never inherited from the
schema. Request DTOs validate and hand a ``dict`` to the service; response DTOs read from
model instances.
"""

from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers

from domains.accounts.models import User

# --------------------------------------------------------------------------------------
# Requests
# --------------------------------------------------------------------------------------


def _validate_password_strength(value: str) -> str:
    try:
        validate_password(value)
    except DjangoValidationError as exc:
        raise serializers.ValidationError(list(exc.messages)) from exc
    return value


class RegisterRequest(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, min_length=8, max_length=128)
    first_name = serializers.CharField(max_length=80, allow_blank=True, required=False, default="")
    last_name = serializers.CharField(max_length=80, allow_blank=True, required=False, default="")
    phone = serializers.CharField(max_length=32, allow_blank=True, required=False, default="")
    address = serializers.CharField(allow_blank=True, required=False, default="")

    def validate_email(self, value: str) -> str:
        return value.strip().lower()

    def validate_password(self, value: str) -> str:
        return _validate_password_strength(value)


class LoginRequest(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)

    def validate_email(self, value: str) -> str:
        return value.strip().lower()


class RefreshRequest(serializers.Serializer):
    refresh = serializers.CharField()


class LogoutRequest(serializers.Serializer):
    refresh = serializers.CharField()


class ChangePasswordRequest(serializers.Serializer):
    current_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True, min_length=8, max_length=128)

    def validate_new_password(self, value: str) -> str:
        return _validate_password_strength(value)


class UpdateMeRequest(serializers.Serializer):
    """Fields a user may change about themselves. Role and status are deliberately absent."""

    first_name = serializers.CharField(max_length=80, allow_blank=True, required=False)
    last_name = serializers.CharField(max_length=80, allow_blank=True, required=False)
    phone = serializers.CharField(max_length=32, allow_blank=True, required=False)
    address = serializers.CharField(allow_blank=True, required=False)


class MemberUpdateRequest(serializers.Serializer):
    """Librarian-only changes to someone else's membership."""

    is_suspended = serializers.BooleanField(required=False)
    suspension_reason = serializers.CharField(max_length=255, allow_blank=True, required=False)
    membership_expires_on = serializers.DateField(required=False, allow_null=True)
    is_active = serializers.BooleanField(required=False)
    phone = serializers.CharField(max_length=32, allow_blank=True, required=False)
    address = serializers.CharField(allow_blank=True, required=False)


# --------------------------------------------------------------------------------------
# Responses
# --------------------------------------------------------------------------------------


class MemberProfileResponse(serializers.Serializer):
    membership_number = serializers.CharField()
    phone = serializers.CharField()
    address = serializers.CharField()
    joined_on = serializers.DateField()
    membership_expires_on = serializers.DateField(allow_null=True)
    is_suspended = serializers.BooleanField()
    suspension_reason = serializers.CharField()
    is_expired = serializers.BooleanField()
    can_borrow = serializers.BooleanField()


class UserResponse(serializers.Serializer):
    id = serializers.IntegerField()
    email = serializers.EmailField()
    first_name = serializers.CharField()
    last_name = serializers.CharField()
    full_name = serializers.CharField()
    role = serializers.ChoiceField(choices=User.Role.choices)
    is_active = serializers.BooleanField()
    date_joined = serializers.DateTimeField()
    profile = serializers.SerializerMethodField()

    def get_profile(self, obj: User) -> dict | None:
        profile = getattr(obj, "member_profile", None)
        if profile is None:
            return None
        return MemberProfileResponse(profile).data


class MemberListItemResponse(serializers.Serializer):
    id = serializers.IntegerField()
    email = serializers.EmailField()
    full_name = serializers.CharField()
    membership_number = serializers.CharField(source="member_profile.membership_number")
    is_active = serializers.BooleanField()
    is_suspended = serializers.BooleanField(source="member_profile.is_suspended")
    membership_expires_on = serializers.DateField(
        source="member_profile.membership_expires_on", allow_null=True
    )
    active_loan_count = serializers.IntegerField(read_only=True)
    unpaid_fine_total = serializers.DecimalField(max_digits=8, decimal_places=2, read_only=True)


class TokenResponse(serializers.Serializer):
    access = serializers.CharField()
    refresh = serializers.CharField()
    user = UserResponse()
