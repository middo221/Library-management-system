import pytest

from domains.accounts import services
from domains.accounts.exceptions import (
    EmailAlreadyRegistered,
    IncorrectPassword,
    InvalidCredentials,
)
from domains.accounts.models import MemberProfile, User
from testing.factories import MemberFactory

pytestmark = pytest.mark.django_db


class TestRegisterMember:
    def test_creates_user_and_profile(self):
        user = services.register_member(
            email="Rosa@Library.test", password="StrongPass123!", first_name="Rosa"
        )

        assert user.email == "rosa@library.test"
        assert user.role == User.Role.MEMBER
        assert user.member_profile.membership_number.startswith("M-")

    def test_membership_numbers_are_unique_and_sequential(self):
        first = services.register_member(email="a@x.test", password="StrongPass123!")
        second = services.register_member(email="b@x.test", password="StrongPass123!")

        assert first.member_profile.membership_number != second.member_profile.membership_number
        assert MemberProfile.objects.count() == 2

    def test_duplicate_email_is_rejected(self):
        services.register_member(email="dup@x.test", password="StrongPass123!")

        with pytest.raises(EmailAlreadyRegistered):
            services.register_member(email="DUP@x.test", password="StrongPass123!")

    def test_password_is_hashed(self):
        user = services.register_member(email="hash@x.test", password="StrongPass123!")

        assert user.password != "StrongPass123!"
        assert user.check_password("StrongPass123!")


class TestAuthenticateUser:
    def test_valid_credentials_return_the_user(self):
        member = MemberFactory(email="login@x.test", password="StrongPass123!")

        assert services.authenticate_user(email="login@x.test", password="StrongPass123!") == member

    def test_wrong_password_raises(self):
        MemberFactory(email="login@x.test", password="StrongPass123!")

        with pytest.raises(InvalidCredentials):
            services.authenticate_user(email="login@x.test", password="nope")

    def test_inactive_user_cannot_authenticate(self):
        MemberFactory(email="off@x.test", password="StrongPass123!", is_active=False)

        with pytest.raises(InvalidCredentials):
            services.authenticate_user(email="off@x.test", password="StrongPass123!")


class TestChangePassword:
    def test_changes_when_current_password_matches(self, member):
        services.change_password(
            user=member, current_password="TestPass123!", new_password="BrandNew456!"
        )
        member.refresh_from_db()

        assert member.check_password("BrandNew456!")

    def test_rejects_wrong_current_password(self, member):
        with pytest.raises(IncorrectPassword):
            services.change_password(
                user=member, current_password="wrong", new_password="BrandNew456!"
            )


class TestUpdateMember:
    def test_librarian_can_suspend_and_reinstate(self, member, librarian):
        services.update_member(
            member=member,
            data={"is_suspended": True, "suspension_reason": "Unreturned items"},
            actor=librarian,
        )
        member.refresh_from_db()
        assert member.member_profile.is_suspended is True

        services.update_member(member=member, data={"is_suspended": False}, actor=librarian)
        member.refresh_from_db()
        assert member.member_profile.is_suspended is False
        assert member.member_profile.suspension_reason == ""
