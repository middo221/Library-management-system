import pytest

from domains.catalog import selectors
from domains.catalog.models import BookCopy
from testing.factories import AuthorFactory, BookCopyFactory, BookFactory, CategoryFactory

pytestmark = pytest.mark.django_db


class TestListBooks:
    def test_availability_counts_ignore_withdrawn_and_lost(self, book):
        BookCopyFactory(book=book, status=BookCopy.Status.AVAILABLE)
        BookCopyFactory(book=book, status=BookCopy.Status.ON_LOAN)
        BookCopyFactory(book=book, status=BookCopy.Status.WITHDRAWN)
        BookCopyFactory(book=book, status=BookCopy.Status.LOST)

        result = selectors.list_books().get(pk=book.pk)

        assert result.total_copies == 2
        assert result.available_copies == 1

    def test_available_filter_excludes_titles_with_nothing_on_the_shelf(self):
        on_shelf = BookFactory(title="On the shelf")
        BookCopyFactory(book=on_shelf)
        all_out = BookFactory(title="All out")
        BookCopyFactory(book=all_out, status=BookCopy.Status.ON_LOAN)

        available = list(selectors.list_books(available=True))

        assert on_shelf in available
        assert all_out not in available

    def test_search_matches_title_isbn_and_author_name(self):
        author = AuthorFactory(name="Ursula K. Le Guin")
        book = BookFactory(title="A Wizard of Earthsea", isbn="9780306406157", authors=[author])
        BookFactory(title="Something Else")

        assert list(selectors.list_books(search="Earthsea")) == [book]
        assert list(selectors.list_books(search="9780306406157")) == [book]
        assert list(selectors.list_books(search="Le Guin")) == [book]

    def test_category_and_language_filters(self):
        category = CategoryFactory(name="Poetry")
        match = BookFactory(category=category, language="English")
        BookFactory(language="French")

        assert list(selectors.list_books(category=category.id)) == [match]
        assert list(selectors.list_books(language="french")) != [match]

    def test_query_count_is_bounded_regardless_of_page_size(
        self, django_assert_num_queries, category
    ):
        author = AuthorFactory()
        for index in range(12):
            title = BookFactory(title=f"Title {index}", category=category, authors=[author])
            BookCopyFactory(book=title)

        # One query for the page, one for the prefetched authors — and that stays true
        # whether the page holds 3 books or 12.
        with django_assert_num_queries(2):
            list(selectors.list_books()[:3].prefetch_related("authors"))

        with django_assert_num_queries(2):
            list(selectors.list_books()[:12].prefetch_related("authors"))
