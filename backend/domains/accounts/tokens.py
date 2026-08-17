"""JWT issuing, rotation and revocation.

``role`` and ``email`` ride along as claims so the SPA can render role-appropriate
navigation on first paint. Authorisation itself always re-reads ``request.user.role`` —
the claim is a rendering hint, never a permission.
"""

from typing import TypedDict

from django.contrib.auth.models import update_last_login
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.settings import api_settings
from rest_framework_simplejwt.tokens import RefreshToken

from domains.accounts.exceptions import InvalidRefreshToken
from domains.accounts.models import User


class TokenPair(TypedDict):
    access: str
    refresh: str


def _decorate(refresh: RefreshToken, user: User) -> None:
    refresh["role"] = user.role
    refresh["email"] = user.email
    refresh["full_name"] = user.full_name


def issue_tokens(user: User) -> TokenPair:
    refresh = RefreshToken.for_user(user)
    _decorate(refresh, user)

    if api_settings.UPDATE_LAST_LOGIN:
        update_last_login(None, user)

    return {"access": str(refresh.access_token), "refresh": str(refresh)}


def rotate_tokens(raw_refresh: str) -> TokenPair:
    """Exchange a refresh token for a fresh pair, blacklisting the presented one."""
    try:
        refresh = RefreshToken(raw_refresh)
    except TokenError as exc:
        raise InvalidRefreshToken() from exc

    if api_settings.BLACKLIST_AFTER_ROTATION:
        try:
            refresh.blacklist()
        except AttributeError as exc:  # pragma: no cover - blacklist app always installed
            raise InvalidRefreshToken() from exc

    refresh.set_jti()
    refresh.set_exp()
    refresh.set_iat()

    return {"access": str(refresh.access_token), "refresh": str(refresh)}


def revoke_refresh_token(raw_refresh: str) -> None:
    try:
        RefreshToken(raw_refresh).blacklist()
    except TokenError as exc:
        raise InvalidRefreshToken() from exc
