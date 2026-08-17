"""ISBN validation. Both ISBN-10 and ISBN-13 are accepted and stored normalised."""

import re

from django.core.exceptions import ValidationError

_SEPARATORS = re.compile(r"[\s-]")


def normalise_isbn(value: str) -> str:
    return _SEPARATORS.sub("", value or "").upper()


def _isbn10_is_valid(isbn: str) -> bool:
    if not re.fullmatch(r"\d{9}[\dX]", isbn):
        return False
    total = sum(
        (10 - index) * (10 if char == "X" else int(char)) for index, char in enumerate(isbn)
    )
    return total % 11 == 0


def _isbn13_is_valid(isbn: str) -> bool:
    if not re.fullmatch(r"\d{13}", isbn):
        return False
    total = sum(int(char) * (1 if index % 2 == 0 else 3) for index, char in enumerate(isbn))
    return total % 10 == 0


def validate_isbn(value: str) -> None:
    isbn = normalise_isbn(value)
    if len(isbn) == 10 and _isbn10_is_valid(isbn):
        return
    if len(isbn) == 13 and _isbn13_is_valid(isbn):
        return
    raise ValidationError(
        "Enter a valid ISBN-10 or ISBN-13 (the check digit did not match).",
        code="invalid_isbn",
    )
