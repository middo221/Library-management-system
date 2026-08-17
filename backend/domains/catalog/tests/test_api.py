import pytest

from domains.catalog.models import BookCopy
from testing.factories import AuthorFactory, BookCopyFactory, BookFactory

pytestmark = pytest.mark.django_db

BOOKS = "/api/v1/books"
AUTHORS = "/api/v1/authors"
CATEGORIES = "/api/v1/categories"


class TestBookList:
    def test_anyone_signed_in_can_browse(self, member_api, book):
        response = member_api.get(BOOKS)

        assert response.status_code == 200
        assert response.data["count"] == 1
        assert response.data["results"][0]["title"] == book.title

    def test_anonymous_browsing_is_401(self, api):
        assert api.get(BOOKS).status_code == 401

    def test_search_and_availability_counts(self, member_api, book):
        BookCopyFactory(book=book)
        BookCopyFactory(book=book, status=BookCopy.Status.ON_LOAN)

        response = member_api.get(BOOKS, {"search": book.title, "available": "true"})

        assert response.data["count"] == 1
        row = response.data["results"][0]
        assert row["total_copies"] == 2
        assert row["available_copies"] == 1

    def test_pagination_shape(self, member_api):
        for index in range(25):
            BookFactory(title=f"Book {index:02d}")

        response = member_api.get(BOOKS, {"page_size": 10})

        assert response.data["count"] == 25
        assert response.data["total_pages"] == 3
        assert len(response.data["results"]) == 10

    def test_page_size_is_capped(self, member_api, book):
        response = member_api.get(BOOKS, {"page_size": 5000})

        assert response.data["page_size"] == 100

    def test_ordering_is_whitelisted(self, member_api):
        BookFactory(title="Bravo")
        BookFactory(title="Alpha")

        response = member_api.get(BOOKS, {"ordering": "-title"})

        assert [row["title"] for row in response.data["results"]] == ["Bravo", "Alpha"]


class TestBookWrites:
    def test_member_cannot_create_a_book(self, member_api):
        response = member_api.post(BOOKS, {"isbn": "9780306406157", "title": "X"}, format="json")

        assert response.status_code == 403
        assert response.data["error"]["code"] == "PERMISSION_DENIED"

    def test_librarian_creates_a_book(self, librarian_api, author, category):
        response = librarian_api.post(
            BOOKS,
            {
                "isbn": "978-0-306-40615-7",
                "title": "Structured Things",
                "author_ids": [author.id],
                "category_id": category.id,
                "published_year": 1998,
            },
            format="json",
        )

        assert response.status_code == 201
        assert response.data["isbn"] == "9780306406157"
        assert response.data["authors"][0]["name"] == author.name
        assert response.data["category"]["name"] == category.name

    def test_invalid_isbn_is_a_field_error(self, librarian_api):
        response = librarian_api.post(
            BOOKS, {"isbn": "9780306406158", "title": "Bad checksum"}, format="json"
        )

        assert response.status_code == 400
        assert response.data["error"]["code"] == "VALIDATION_ERROR"
        assert "isbn" in response.data["error"]["details"]

    def test_patch_updates_a_book(self, librarian_api, book):
        response = librarian_api.patch(
            f"{BOOKS}/{book.id}", {"title": "Renamed", "page_count": 321}, format="json"
        )

        assert response.status_code == 200
        assert response.data["title"] == "Renamed"
        assert response.data["page_count"] == 321

    def test_delete_is_refused_while_copies_exist(self, librarian_api, book):
        BookCopyFactory(book=book)

        response = librarian_api.delete(f"{BOOKS}/{book.id}")

        assert response.status_code == 409
        assert response.data["error"]["code"] == "BOOK_HAS_COPIES"

    def test_unknown_book_is_404_in_the_envelope(self, member_api):
        response = member_api.get(f"{BOOKS}/9999")

        assert response.status_code == 404
        assert response.data["error"]["code"] == "NOT_FOUND"


class TestCopies:
    def test_list_copies_for_a_book(self, member_api, book):
        BookCopyFactory(book=book, barcode="L00101")

        response = member_api.get(f"{BOOKS}/{book.id}/copies")

        assert response.status_code == 200
        assert response.data[0]["barcode"] == "L00101"

    def test_member_cannot_add_a_copy(self, member_api, book):
        response = member_api.post(
            f"{BOOKS}/{book.id}/copies", {"barcode": "L00102"}, format="json"
        )

        assert response.status_code == 403

    def test_librarian_adds_a_copy(self, librarian_api, book):
        response = librarian_api.post(
            f"{BOOKS}/{book.id}/copies",
            {"barcode": "L00102", "call_number": "823.912 JOY"},
            format="json",
        )

        assert response.status_code == 201
        assert response.data["status"] == "AVAILABLE"

    def test_duplicate_barcode_is_409(self, librarian_api, book):
        BookCopyFactory(barcode="L00103")

        response = librarian_api.post(
            f"{BOOKS}/{book.id}/copies", {"barcode": "L00103"}, format="json"
        )

        assert response.status_code == 409
        assert response.data["error"]["code"] == "DUPLICATE_BARCODE"

    def test_member_cannot_read_the_copy_admin_endpoint(self, member_api, copy):
        assert member_api.get(f"/api/v1/copies/{copy.id}").status_code == 403


class TestAuthorsAndCategories:
    def test_member_can_list_authors(self, member_api):
        AuthorFactory(name="Italo Calvino")

        response = member_api.get(AUTHORS)

        assert response.status_code == 200
        assert response.data["results"][0]["name"] == "Italo Calvino"

    def test_member_cannot_create_an_author(self, member_api):
        assert member_api.post(AUTHORS, {"name": "Nope"}, format="json").status_code == 403

    def test_librarian_creates_an_author(self, librarian_api):
        response = librarian_api.post(
            AUTHORS,
            {"name": "Italo Calvino", "birth_year": 1923, "death_year": 1985},
            format="json",
        )

        assert response.status_code == 201

    def test_death_before_birth_is_rejected(self, librarian_api):
        response = librarian_api.post(
            AUTHORS, {"name": "Impossible", "birth_year": 1985, "death_year": 1923}, format="json"
        )

        assert response.status_code == 400
        assert "death_year" in response.data["error"]["details"]

    def test_category_slug_is_generated(self, librarian_api):
        response = librarian_api.post(CATEGORIES, {"name": "Local History"}, format="json")

        assert response.status_code == 201
        assert response.data["slug"] == "local-history"

    def test_category_with_books_cannot_be_deleted(self, librarian_api, book):
        response = librarian_api.delete(f"{CATEGORIES}/{book.category_id}")

        assert response.status_code == 409
        assert response.data["error"]["code"] == "CATEGORY_HAS_BOOKS"
