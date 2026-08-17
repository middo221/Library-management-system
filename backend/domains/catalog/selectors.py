"""Catalogue read queries.

Availability is computed with conditional aggregates in the same query as the list, so a
page of 100 books costs the same number of round trips as a page of 1.
"""

from django.db.models import Count, Q, QuerySet

from domains.catalog.models import Author, Book, BookCopy, Category

_ORDERING_WHITELIST = {
    "title": "title",
    "-title": "-title",
    "published_year": "published_year",
    "-published_year": "-published_year",
    "created_at": "created_at",
    "-created_at": "-created_at",
}


def _with_copy_counts(queryset: QuerySet[Book]) -> QuerySet[Book]:
    return queryset.annotate(
        total_copies=Count(
            "copies",
            filter=Q(copies__status__in=BookCopy.IN_COLLECTION_STATUSES),
            distinct=True,
        ),
        available_copies=Count(
            "copies",
            filter=Q(copies__status=BookCopy.Status.AVAILABLE),
            distinct=True,
        ),
    )


def list_books(
    *,
    search: str = "",
    category: int | None = None,
    author: int | None = None,
    language: str = "",
    available: bool | None = None,
    ordering: str = "title",
) -> QuerySet[Book]:
    queryset = _with_copy_counts(
        Book.objects.select_related("category").prefetch_related("authors")
    )

    if search:
        queryset = queryset.filter(
            Q(title__icontains=search)
            | Q(subtitle__icontains=search)
            | Q(isbn__icontains=search)
            | Q(authors__name__icontains=search)
        ).distinct()

    if category is not None:
        queryset = queryset.filter(category_id=category)

    if author is not None:
        queryset = queryset.filter(authors__id=author)

    if language:
        queryset = queryset.filter(language__iexact=language)

    if available is True:
        queryset = queryset.filter(available_copies__gt=0)
    elif available is False:
        queryset = queryset.filter(available_copies=0)

    return queryset.order_by(_ORDERING_WHITELIST.get(ordering, "title"), "id")


def get_book(*, book_id: int) -> Book | None:
    return (
        _with_copy_counts(Book.objects.select_related("category").prefetch_related("authors"))
        .filter(pk=book_id)
        .first()
    )


def list_copies(*, book_id: int | None = None, status: str = "") -> QuerySet[BookCopy]:
    queryset = BookCopy.objects.select_related("book")
    if book_id is not None:
        queryset = queryset.filter(book_id=book_id)
    if status:
        queryset = queryset.filter(status=status)
    return queryset.order_by("barcode")


def get_copy(*, copy_id: int) -> BookCopy | None:
    return BookCopy.objects.select_related("book").filter(pk=copy_id).first()


def get_copy_by_barcode(*, barcode: str) -> BookCopy | None:
    return BookCopy.objects.select_related("book").filter(barcode=barcode.strip()).first()


def list_authors(*, search: str = "") -> QuerySet[Author]:
    queryset = Author.objects.annotate(book_count=Count("books", distinct=True))
    if search:
        queryset = queryset.filter(name__icontains=search)
    return queryset.order_by("name")


def get_author(*, author_id: int) -> Author | None:
    return (
        Author.objects.annotate(book_count=Count("books", distinct=True))
        .filter(pk=author_id)
        .first()
    )


def list_categories() -> QuerySet[Category]:
    return Category.objects.annotate(book_count=Count("books", distinct=True)).order_by("name")


def get_category(*, category_id: int) -> Category | None:
    return (
        Category.objects.annotate(book_count=Count("books", distinct=True))
        .filter(pk=category_id)
        .first()
    )
