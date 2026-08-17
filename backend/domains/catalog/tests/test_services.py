import pytest
from django.core.exceptions import ValidationError as DjangoValidationError

from domains.catalog import services
from domains.catalog.exceptions import (
    AuthorNotFound,
    BookHasCopies,
    CategoryNotFound,
    CopyOnLoan,
    DuplicateBarcode,
    DuplicateIsbn,
)
from domains.catalog.models import Book, BookCopy
from domains.catalog.validators import validate_isbn
from testing.factories import AuthorFactory, BookCopyFactory, BookFactory, CategoryFactory

pytestmark = pytest.mark.django_db


class TestIsbnValidation:
    @pytest.mark.parametrize("isbn", ["9780306406157", "0306406152", "080442957X"])
    def test_accepts_valid_isbns(self, isbn):
        validate_isbn(isbn)

    @pytest.mark.parametrize("isbn", ["9780306406158", "0306406153", "12345", "abcdefghij"])
    def test_rejects_invalid_isbns(self, isbn):
        with pytest.raises(DjangoValidationError):
            validate_isbn(isbn)


class TestCreateBook:
    def test_creates_with_authors_and_category(self, librarian):
        author = AuthorFactory()
        category = CategoryFactory()

        book = services.create_book(
            data={
                "isbn": "9780306406157",
                "title": "Structured Things",
                "author_ids": [author.id],
                "category_id": category.id,
            },
            actor=librarian,
        )

        assert book.authors.count() == 1
        assert book.category == category

    def test_duplicate_isbn_is_rejected(self, librarian):
        BookFactory(isbn="9780306406157")

        with pytest.raises(DuplicateIsbn):
            services.create_book(data={"isbn": "9780306406157", "title": "Again"}, actor=librarian)

    def test_unknown_author_is_rejected(self, librarian):
        with pytest.raises(AuthorNotFound):
            services.create_book(
                data={"isbn": "9780306406157", "title": "X", "author_ids": [999]}, actor=librarian
            )

    def test_unknown_category_is_rejected(self, librarian):
        with pytest.raises(CategoryNotFound):
            services.create_book(
                data={"isbn": "9780306406157", "title": "X", "category_id": 999}, actor=librarian
            )


class TestUpdateAndDeleteBook:
    def test_update_replaces_authors(self, librarian, book):
        replacement = AuthorFactory()

        services.update_book(
            book=book, data={"author_ids": [replacement.id], "title": "Renamed"}, actor=librarian
        )
        book.refresh_from_db()

        assert book.title == "Renamed"
        assert list(book.authors.all()) == [replacement]

    def test_category_can_be_cleared(self, librarian, book):
        services.update_book(book=book, data={"category_id": None}, actor=librarian)
        book.refresh_from_db()

        assert book.category is None

    def test_cannot_delete_a_book_with_copies(self, librarian, book):
        BookCopyFactory(book=book)

        with pytest.raises(BookHasCopies):
            services.delete_book(book=book, actor=librarian)

    def test_deletes_a_book_with_no_copies(self, librarian, book):
        services.delete_book(book=book, actor=librarian)

        assert not Book.objects.filter(pk=book.pk).exists()


class TestCopies:
    def test_add_copy(self, librarian, book):
        copy = services.add_copy(
            book=book, data={"barcode": "L00101", "call_number": "823.912 JOY"}, actor=librarian
        )

        assert copy.status == BookCopy.Status.AVAILABLE
        assert copy.book == book

    def test_duplicate_barcode_is_rejected(self, librarian, book):
        BookCopyFactory(barcode="L00101")

        with pytest.raises(DuplicateBarcode):
            services.add_copy(book=book, data={"barcode": "L00101"}, actor=librarian)

    def test_cannot_delete_a_copy_on_loan(self, librarian, book):
        copy = BookCopyFactory(book=book, status=BookCopy.Status.ON_LOAN)

        with pytest.raises(CopyOnLoan):
            services.delete_copy(copy=copy, actor=librarian)

    def test_cannot_change_status_while_on_loan(self, librarian, book):
        copy = BookCopyFactory(book=book, status=BookCopy.Status.ON_LOAN)

        with pytest.raises(CopyOnLoan):
            services.update_copy(
                copy=copy, data={"status": BookCopy.Status.DAMAGED}, actor=librarian
            )

    def test_status_can_change_when_the_copy_is_on_the_shelf(self, librarian, copy):
        updated = services.update_copy(
            copy=copy, data={"status": BookCopy.Status.DAMAGED}, actor=librarian
        )

        assert updated.status == BookCopy.Status.DAMAGED
