"""Account workflows. No DRF imports here by design."""

from typing import Any

from django.contrib.auth import authenticate
from django.db import transaction

from domains.accounts.exceptions import (
    EmailAlreadyRegistered,
    IncorrectPassword,
    InvalidCredentials,
)
from domains.accounts.models import MemberProfile, User
from domains.common.logging import log_action


@transaction.atomic
def register_member(
    *,
    email: str,
    password: str,
    first_name: str = "",
    last_name: str = "",
    phone: str = "",
    address: str = "",
) -> User:
    email = email.strip().lower()
    if User.objects.filter(email__iexact=email).exists():
        raise EmailAlreadyRegistered()

    user = User.objects.create_user(
        email=email,
        password=password,
        first_name=first_name,
        last_name=last_name,
        role=User.Role.MEMBER,
    )
    MemberProfile.objects.create(
        user=user,
        membership_number=MemberProfile.next_membership_number(),
        phone=phone,
        address=address,
    )
    log_action("member.registered", actor=user, user_id=user.id)
    return user


def authenticate_user(*, email: str, password: str) -> User:
    user = authenticate(username=email.strip().lower(), password=password)
    if user is None or not user.is_active:
        raise InvalidCredentials()
    return user


@transaction.atomic
def change_password(*, user: User, current_password: str, new_password: str) -> None:
    if not user.check_password(current_password):
        raise IncorrectPassword()
    user.set_password(new_password)
    user.save(update_fields=["password"])
    log_action("user.password_changed", actor=user, user_id=user.id)


@transaction.atomic
def update_own_profile(*, user: User, data: dict[str, Any]) -> User:
    user_fields = {key: data[key] for key in ("first_name", "last_name") if key in data}
    if user_fields:
        for field, value in user_fields.items():
            setattr(user, field, value)
        user.save(update_fields=list(user_fields))

    profile = getattr(user, "member_profile", None)
    profile_fields = {key: data[key] for key in ("phone", "address") if key in data}
    if profile is not None and profile_fields:
        for field, value in profile_fields.items():
            setattr(profile, field, value)
        profile.save(update_fields=[*profile_fields, "updated_at"])

    log_action("user.profile_updated", actor=user, user_id=user.id, fields=",".join(data))
    user.refresh_from_db()
    return user


@transaction.atomic
def update_member(*, member: User, data: dict[str, Any], actor: User) -> User:
    """Librarian-side membership administration: suspend, reinstate, extend, deactivate."""
    profile = member.member_profile

    profile_fields = {
        key: data[key]
        for key in (
            "is_suspended",
            "suspension_reason",
            "membership_expires_on",
            "phone",
            "address",
        )
        if key in data
    }
    if "is_suspended" in profile_fields and profile_fields["is_suspended"] is False:
        profile_fields.setdefault("suspension_reason", "")

    if profile_fields:
        for field, value in profile_fields.items():
            setattr(profile, field, value)
        profile.save(update_fields=[*profile_fields, "updated_at"])

    if "is_active" in data:
        member.is_active = data["is_active"]
        member.save(update_fields=["is_active"])

    log_action(
        "member.updated",
        actor=actor,
        member_id=member.id,
        membership_number=profile.membership_number,
        fields=",".join(data),
    )
    member.refresh_from_db()
    return member
