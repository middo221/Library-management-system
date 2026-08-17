"""Shared pytest fixtures.

``api`` is unauthenticated; ``member_api`` and ``librarian_api`` carry a real ``Bearer``
token issued the same way the login endpoint issues one — so auth is exercised, not stubbed.
"""

from datetime import timedelta

import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from domains.accounts.tokens import issue_tokens
from testing.factories import (
    AuthorFactory,
    BookCopyFactory,
    BookFactory,
    CategoryFactory,
    LibrarianFactory,
    LoanFactory,
    MemberFactory,
)


@pytest.fixture
def api() -> APIClient:
    return APIClient()


@pytest.fixture
def member(db):
    return MemberFactory()


@pytest.fixture
def other_member(db):
    return MemberFactory()


@pytest.fixture
def librarian(db):
    return LibrarianFactory()


def _authenticated_client(user) -> APIClient:
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {issue_tokens(user)['access']}")
    return client


@pytest.fixture
def member_api(member) -> APIClient:
    return _authenticated_client(member)


@pytest.fixture
def other_member_api(other_member) -> APIClient:
    return _authenticated_client(other_member)


@pytest.fixture
def librarian_api(librarian) -> APIClient:
    return _authenticated_client(librarian)


@pytest.fixture
def author(db):
    return AuthorFactory()


@pytest.fixture
def category(db):
    return CategoryFactory()


@pytest.fixture
def book(db, author, category):
    return BookFactory(authors=[author], category=category)


@pytest.fixture
def copy(db, book):
    return BookCopyFactory(book=book)


@pytest.fixture
def overdue_loan(db, member, copy):
    """A loan that went out three weeks ago and is a week past its date."""
    return LoanFactory(
        copy=copy,
        member=member,
        checked_out_at=timezone.now() - timedelta(days=21),
        due_on=timezone.localdate() - timedelta(days=7),
    )
