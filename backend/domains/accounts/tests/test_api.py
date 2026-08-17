import pytest
from django.urls import reverse

from domains.accounts.tokens import issue_tokens
from testing.factories import MemberFactory

pytestmark = pytest.mark.django_db

REGISTER = "/api/v1/auth/register"
LOGIN = "/api/v1/auth/login"
REFRESH = "/api/v1/auth/refresh"
LOGOUT = "/api/v1/auth/logout"
ME = "/api/v1/auth/me"
CHANGE_PASSWORD = "/api/v1/auth/change-password"
MEMBERS = "/api/v1/members"


class TestRegisterLoginMe:
    def test_full_loop(self, api):
        registration = api.post(
            REGISTER,
            {"email": "new@x.test", "password": "StrongPass123!", "first_name": "New"},
            format="json",
        )
        assert registration.status_code == 201
        assert registration.data["user"]["role"] == "MEMBER"
        assert registration.data["user"]["profile"]["membership_number"].startswith("M-")

        login = api.post(
            LOGIN, {"email": "new@x.test", "password": "StrongPass123!"}, format="json"
        )
        assert login.status_code == 200

        api.credentials(HTTP_AUTHORIZATION=f"Bearer {login.data['access']}")
        me = api.get(ME)
        assert me.status_code == 200
        assert me.data["email"] == "new@x.test"

    def test_password_never_appears_in_a_response(self, api):
        response = api.post(
            REGISTER, {"email": "quiet@x.test", "password": "StrongPass123!"}, format="json"
        )
        body = str(response.data)

        assert "StrongPass123!" not in body
        assert "password" not in response.data["user"]

    def test_weak_password_is_rejected_with_field_details(self, api):
        response = api.post(
            REGISTER, {"email": "weak@x.test", "password": "12345678"}, format="json"
        )

        assert response.status_code == 400
        assert response.data["error"]["code"] == "VALIDATION_ERROR"
        assert "password" in response.data["error"]["details"]

    def test_duplicate_email_uses_its_own_code(self, api):
        MemberFactory(email="taken@x.test")

        response = api.post(
            REGISTER, {"email": "taken@x.test", "password": "StrongPass123!"}, format="json"
        )

        assert response.status_code == 409
        assert response.data["error"]["code"] == "EMAIL_ALREADY_REGISTERED"

    def test_bad_credentials_return_401_envelope(self, api):
        MemberFactory(email="real@x.test", password="StrongPass123!")

        response = api.post(LOGIN, {"email": "real@x.test", "password": "wrong"}, format="json")

        assert response.status_code == 401
        assert response.data["error"]["code"] == "INVALID_CREDENTIALS"

    def test_me_without_a_token_is_401_in_the_envelope(self, api):
        response = api.get(ME)

        assert response.status_code == 401
        assert response.data["error"]["code"] == "NOT_AUTHENTICATED"
        assert set(response.data["error"]) == {"code", "message", "details"}

    def test_login_claims_carry_the_role(self, member):
        from rest_framework_simplejwt.tokens import AccessToken

        tokens = issue_tokens(member)
        claims = AccessToken(tokens["access"])

        assert claims["role"] == "MEMBER"
        assert claims["email"] == member.email


class TestRefreshRotation:
    def test_refresh_rotates_and_blacklists_the_old_token(self, api, member):
        original = issue_tokens(member)["refresh"]

        first = api.post(REFRESH, {"refresh": original}, format="json")
        assert first.status_code == 200
        assert first.data["refresh"] != original

        replay = api.post(REFRESH, {"refresh": original}, format="json")
        assert replay.status_code == 401
        assert replay.data["error"]["code"] == "INVALID_REFRESH_TOKEN"

    def test_logout_blacklists_the_presented_refresh_token(self, api, member, member_api):
        tokens = issue_tokens(member)

        logout = member_api.post(LOGOUT, {"refresh": tokens["refresh"]}, format="json")
        assert logout.status_code == 200

        reuse = api.post(REFRESH, {"refresh": tokens["refresh"]}, format="json")
        assert reuse.status_code == 401


class TestMeUpdates:
    def test_member_updates_their_own_profile(self, member_api):
        response = member_api.patch(
            ME, {"first_name": "Rosa", "phone": "0207 946 0018"}, format="json"
        )

        assert response.status_code == 200
        assert response.data["first_name"] == "Rosa"
        assert response.data["profile"]["phone"] == "0207 946 0018"

    def test_change_password_requires_the_current_one(self, member_api):
        response = member_api.post(
            CHANGE_PASSWORD,
            {"current_password": "wrong", "new_password": "BrandNew456!"},
            format="json",
        )

        assert response.status_code == 400
        assert response.data["error"]["code"] == "INCORRECT_PASSWORD"

    def test_change_password_succeeds_and_the_new_one_works(self, api, member, member_api):
        changed = member_api.post(
            CHANGE_PASSWORD,
            {"current_password": "TestPass123!", "new_password": "BrandNew456!"},
            format="json",
        )
        assert changed.status_code == 200

        login = api.post(LOGIN, {"email": member.email, "password": "BrandNew456!"}, format="json")
        assert login.status_code == 200


class TestMembersEndpoint:
    def test_librarian_lists_members(self, librarian_api, member):
        response = librarian_api.get(MEMBERS)

        assert response.status_code == 200
        assert response.data["count"] == 1
        assert response.data["results"][0]["membership_number"] == (
            member.member_profile.membership_number
        )

    def test_member_gets_403_on_a_librarian_endpoint(self, member_api):
        response = member_api.get(MEMBERS)

        assert response.status_code == 403
        assert response.data["error"]["code"] == "PERMISSION_DENIED"

    def test_librarian_can_suspend_a_member(self, librarian_api, member):
        response = librarian_api.patch(
            f"{MEMBERS}/{member.id}",
            {"is_suspended": True, "suspension_reason": "Lost book unresolved"},
            format="json",
        )

        assert response.status_code == 200
        assert response.data["profile"]["is_suspended"] is True
        assert response.data["profile"]["can_borrow"] is False

    def test_search_matches_membership_number(self, librarian_api, member):
        number = member.member_profile.membership_number

        response = librarian_api.get(MEMBERS, {"search": number})

        assert response.data["count"] == 1

    def test_unknown_member_is_404(self, librarian_api):
        response = librarian_api.get(f"{MEMBERS}/9999")

        assert response.status_code == 404
        assert response.data["error"]["code"] == "NOT_A_MEMBER"


def test_health_endpoint_is_public(api):
    assert api.get(reverse("health")).status_code == 200
