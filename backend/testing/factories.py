"""Factories for every model. Tests build their world through these, never through fixtures
files, so a change to a required field breaks one place instead of forty."""

from datetime import timedelta

import factory
from django.utils import timezone

from domains.accounts.models import MemberProfile, User
from domains.catalog.models import Author, Book, BookCopy, Category
from domains.circulation.models import Fine, Loan, Reservation


class UserFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = User
        skip_postgeneration_save = True

    email = factory.Sequence(lambda n: f"user{n}@library.test")
    first_name = "Test"
    last_name = factory.Sequence(lambda n: f"User{n}")
    role = User.Role.MEMBER

    @factory.post_generation
    def password(self, create, extracted, **kwargs):
        if not create:
            return
        self.set_password(extracted or "TestPass123!")
        self.save(update_fields=["password"])


class LibrarianFactory(UserFactory):
    email = factory.Sequence(lambda n: f"librarian{n}@library.test")
    role = User.Role.LIBRARIAN
    is_staff = True


class MemberProfileFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = MemberProfile

    user = factory.SubFactory(UserFactory)
    membership_number = factory.Sequence(lambda n: f"M-{n + 1:06d}")


class MemberFactory(UserFactory):
    """A member with the profile they cannot borrow without."""

    profile = factory.RelatedFactory(MemberProfileFactory, factory_related_name="user")


class AuthorFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Author

    name = factory.Sequence(lambda n: f"Author {n}")


class CategoryFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Category

    name = factory.Sequence(lambda n: f"Category {n}")


def _isbn13(seed: int) -> str:
    body = f"978{seed:09d}"
    total = sum(int(char) * (1 if index % 2 == 0 else 3) for index, char in enumerate(body))
    return body + str((10 - total % 10) % 10)


class BookFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Book
        skip_postgeneration_save = True

    isbn = factory.Sequence(_isbn13)
    title = factory.Sequence(lambda n: f"Book Title {n}")
    category = factory.SubFactory(CategoryFactory)
    published_year = 2001
    language = "English"

    @factory.post_generation
    def authors(self, create, extracted, **kwargs):
        if not create:
            return
        for author in extracted or []:
            self.authors.add(author)


class BookCopyFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = BookCopy

    book = factory.SubFactory(BookFactory)
    barcode = factory.Sequence(lambda n: f"BC{n:07d}")
    call_number = "823.912 TES"
    status = BookCopy.Status.AVAILABLE


class LoanFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Loan

    copy = factory.SubFactory(BookCopyFactory, status=BookCopy.Status.ON_LOAN)
    member = factory.SubFactory(MemberFactory)
    due_on = factory.LazyFunction(lambda: timezone.localdate() + timedelta(days=14))


class ReservationFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Reservation

    book = factory.SubFactory(BookFactory)
    member = factory.SubFactory(MemberFactory)


class FineFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Fine

    loan = factory.SubFactory(LoanFactory)
    member = factory.SelfAttribute("loan.member")
    amount = "5.00"
    reason = Fine.Reason.OVERDUE
