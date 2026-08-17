"""Catalogue mutations. Rules that concern the state of the collection live here."""

from typing import Any

from django.db import transaction

from domains.catalog.exceptions import (
    AuthorHasBooks,
    AuthorNotFound,
    BookHasCopies,
    CategoryHasBooks,
    CategoryNotFound,
    CopyOnLoan,
    DuplicateBarcode,
    DuplicateIsbn,
)
from domains.catalog.models import Author, Book, BookCopy, Category
from domains.common.logging import log_action

_BOOK_SCALAR_FIELDS = (
    "isbn",
    "title",
    "subtitle",
    "publisher",
    "published_year",
    "language",
    "page_count",
    "description",
    "cover_url",
)


def _resolve_authors(data: dict[str, Any]) -> list[int] | None:
    """``None`` means "leave the existing links alone"; a list means "set them to this"."""
    author_ids = data.get("author_ids")
    if author_ids is None:
        return None

    found = set(Author.objects.filter(id__in=author_ids).values_list("id", flat=True))
    missing = sorted(set(author_ids) - found)
    if missing:
        raise AuthorNotFound("One or more authors do not exist.", details={"author_ids": missing})
    return list(author_ids)


def _resolve_category(data: dict[str, Any]) -> Category | None:
    """Only called when ``category_id`` is present; ``None`` clears the link."""
    category_id = data["category_id"]
    if category_id is None:
        return None
    category = Category.objects.filter(pk=category_id).first()
    if category is None:
        raise CategoryNotFound(details={"category_id": category_id})
    return category


@transaction.atomic
def create_book(*, data: dict[str, Any], actor) -> Book:
    if Book.objects.filter(isbn=data["isbn"]).exists():
        raise DuplicateIsbn(details={"isbn": data["isbn"]})

    author_ids = _resolve_authors(data)
    category = _resolve_category(data) if "category_id" in data else None

    book = Book.objects.create(
        **{field: data[field] for field in _BOOK_SCALAR_FIELDS if field in data},
        category=category,
    )
    if author_ids:
        book.authors.set(author_ids)

    log_action("book.created", actor=actor, book_id=book.id, isbn=book.isbn)
    return book


@transaction.atomic
def update_book(*, book: Book, data: dict[str, Any], actor) -> Book:
    if "isbn" in data and Book.objects.filter(isbn=data["isbn"]).exclude(pk=book.pk).exists():
        raise DuplicateIsbn(details={"isbn": data["isbn"]})

    author_ids = _resolve_authors(data)

    changed = [field for field in _BOOK_SCALAR_FIELDS if field in data]
    for field in changed:
        setattr(book, field, data[field])

    if "category_id" in data:
        book.category = _resolve_category(data)
        changed.append("category")

    if changed:
        book.save(update_fields=[*changed, "updated_at"])
    if author_ids is not None:
        book.authors.set(author_ids)

    log_action("book.updated", actor=actor, book_id=book.id, fields=",".join(data))
    return book


@transaction.atomic
def delete_book(*, book: Book, actor) -> None:
    if book.copies.exists():
        raise BookHasCopies(details={"copy_count": book.copies.count()})
    book_id, isbn = book.id, book.isbn
    book.delete()
    log_action("book.deleted", actor=actor, book_id=book_id, isbn=isbn)


@transaction.atomic
def add_copy(*, book: Book, data: dict[str, Any], actor) -> BookCopy:
    barcode = data["barcode"]
    if BookCopy.objects.filter(barcode=barcode).exists():
        raise DuplicateBarcode(details={"barcode": barcode})

    fields = {key: value for key, value in data.items() if value is not None}
    copy = BookCopy.objects.create(book=book, **fields)

    log_action("copy.created", actor=actor, copy_id=copy.id, barcode=copy.barcode, book_id=book.id)
    return copy


@transaction.atomic
def update_copy(*, copy: BookCopy, data: dict[str, Any], actor) -> BookCopy:
    if "status" in data and copy.status == BookCopy.Status.ON_LOAN:
        # Status while on loan is owned by circulation; changing it here would desynchronise
        # the loan record from the shelf.
        raise CopyOnLoan("Return this copy before changing its status.")

    for field, value in data.items():
        setattr(copy, field, value)
    if data:
        copy.save(update_fields=[*data, "updated_at"])

    log_action("copy.updated", actor=actor, copy_id=copy.id, fields=",".join(data))
    return copy


@transaction.atomic
def delete_copy(*, copy: BookCopy, actor) -> None:
    if copy.status == BookCopy.Status.ON_LOAN:
        raise CopyOnLoan(details={"barcode": copy.barcode})
    copy_id, barcode = copy.id, copy.barcode
    copy.delete()
    log_action("copy.deleted", actor=actor, copy_id=copy_id, barcode=barcode)


# --------------------------------------------------------------------------------------
# Authors and categories
# --------------------------------------------------------------------------------------


@transaction.atomic
def create_author(*, data: dict[str, Any], actor) -> Author:
    author = Author.objects.create(**data)
    log_action("author.created", actor=actor, author_id=author.id)
    return author


@transaction.atomic
def update_author(*, author: Author, data: dict[str, Any], actor) -> Author:
    for field, value in data.items():
        setattr(author, field, value)
    if data:
        author.save(update_fields=[*data, "updated_at"])
    log_action("author.updated", actor=actor, author_id=author.id)
    return author


@transaction.atomic
def delete_author(*, author: Author, actor) -> None:
    if author.books.exists():
        raise AuthorHasBooks(details={"book_count": author.books.count()})
    author_id = author.id
    author.delete()
    log_action("author.deleted", actor=actor, author_id=author_id)


@transaction.atomic
def create_category(*, data: dict[str, Any], actor) -> Category:
    category = Category.objects.create(**data)
    log_action("category.created", actor=actor, category_id=category.id)
    return category


@transaction.atomic
def update_category(*, category: Category, data: dict[str, Any], actor) -> Category:
    for field, value in data.items():
        setattr(category, field, value)
    if data:
        category.save()
    log_action("category.updated", actor=actor, category_id=category.id)
    return category


@transaction.atomic
def delete_category(*, category: Category, actor) -> None:
    if category.books.exists():
        raise CategoryHasBooks(details={"book_count": category.books.count()})
    category_id = category.id
    category.delete()
    log_action("category.deleted", actor=actor, category_id=category_id)
