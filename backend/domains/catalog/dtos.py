"""Catalogue DTOs. List and detail variants are separate on purpose — the grid does not
need descriptions, and the detail page does not want to guess at nesting depth."""

from rest_framework import serializers

from domains.catalog.models import BookCopy
from domains.catalog.validators import normalise_isbn

# --------------------------------------------------------------------------------------
# Authors and categories
# --------------------------------------------------------------------------------------


class AuthorResponse(serializers.Serializer):
    id = serializers.IntegerField()
    name = serializers.CharField()
    bio = serializers.CharField()
    birth_year = serializers.IntegerField(allow_null=True)
    death_year = serializers.IntegerField(allow_null=True)
    book_count = serializers.IntegerField(read_only=True, required=False)


class AuthorSummaryResponse(serializers.Serializer):
    id = serializers.IntegerField()
    name = serializers.CharField()


class AuthorWriteRequest(serializers.Serializer):
    name = serializers.CharField(max_length=180)
    bio = serializers.CharField(allow_blank=True, required=False, default="")
    birth_year = serializers.IntegerField(
        required=False, allow_null=True, min_value=0, max_value=2200
    )
    death_year = serializers.IntegerField(
        required=False, allow_null=True, min_value=0, max_value=2200
    )

    def validate(self, attrs: dict) -> dict:
        birth, death = attrs.get("birth_year"), attrs.get("death_year")
        if birth and death and death < birth:
            raise serializers.ValidationError(
                {"death_year": "Death year cannot precede birth year."}
            )
        return attrs


class CategoryResponse(serializers.Serializer):
    id = serializers.IntegerField()
    name = serializers.CharField()
    slug = serializers.CharField()
    description = serializers.CharField()
    book_count = serializers.IntegerField(read_only=True, required=False)


class CategorySummaryResponse(serializers.Serializer):
    id = serializers.IntegerField()
    name = serializers.CharField()
    slug = serializers.CharField()


class CategoryWriteRequest(serializers.Serializer):
    name = serializers.CharField(max_length=120)
    description = serializers.CharField(allow_blank=True, required=False, default="")


# --------------------------------------------------------------------------------------
# Copies
# --------------------------------------------------------------------------------------


class CopyResponse(serializers.Serializer):
    id = serializers.IntegerField()
    book_id = serializers.IntegerField()
    book_title = serializers.CharField(source="book.title", read_only=True)
    barcode = serializers.CharField()
    call_number = serializers.CharField()
    status = serializers.ChoiceField(choices=BookCopy.Status.choices)
    acquired_on = serializers.DateField()
    condition_note = serializers.CharField()
    replacement_cost = serializers.DecimalField(max_digits=8, decimal_places=2, allow_null=True)


class CopyCreateRequest(serializers.Serializer):
    barcode = serializers.CharField(max_length=32)
    call_number = serializers.CharField(max_length=40, allow_blank=True, required=False, default="")
    acquired_on = serializers.DateField(required=False)
    condition_note = serializers.CharField(
        max_length=255, allow_blank=True, required=False, default=""
    )
    replacement_cost = serializers.DecimalField(
        max_digits=8, decimal_places=2, required=False, allow_null=True, min_value=0
    )

    def validate_barcode(self, value: str) -> str:
        return value.strip()


class CopyUpdateRequest(serializers.Serializer):
    call_number = serializers.CharField(max_length=40, allow_blank=True, required=False)
    status = serializers.ChoiceField(choices=BookCopy.Status.choices, required=False)
    condition_note = serializers.CharField(max_length=255, allow_blank=True, required=False)
    replacement_cost = serializers.DecimalField(
        max_digits=8, decimal_places=2, required=False, allow_null=True, min_value=0
    )


# --------------------------------------------------------------------------------------
# Books
# --------------------------------------------------------------------------------------


class BookListItemResponse(serializers.Serializer):
    id = serializers.IntegerField()
    isbn = serializers.CharField()
    title = serializers.CharField()
    subtitle = serializers.CharField()
    authors = AuthorSummaryResponse(many=True)
    category = CategorySummaryResponse(allow_null=True)
    published_year = serializers.IntegerField(allow_null=True)
    language = serializers.CharField()
    cover_url = serializers.CharField()
    total_copies = serializers.IntegerField(read_only=True)
    available_copies = serializers.IntegerField(read_only=True)


class BookResponse(serializers.Serializer):
    id = serializers.IntegerField()
    isbn = serializers.CharField()
    title = serializers.CharField()
    subtitle = serializers.CharField()
    authors = AuthorSummaryResponse(many=True)
    category = CategorySummaryResponse(allow_null=True)
    publisher = serializers.CharField()
    published_year = serializers.IntegerField(allow_null=True)
    language = serializers.CharField()
    page_count = serializers.IntegerField(allow_null=True)
    description = serializers.CharField()
    cover_url = serializers.CharField()
    total_copies = serializers.IntegerField(read_only=True)
    available_copies = serializers.IntegerField(read_only=True)
    created_at = serializers.DateTimeField()


class BookCreateRequest(serializers.Serializer):
    isbn = serializers.CharField(max_length=20)
    title = serializers.CharField(max_length=300)
    subtitle = serializers.CharField(max_length=300, allow_blank=True, required=False, default="")
    author_ids = serializers.ListField(
        child=serializers.IntegerField(), required=False, default=list
    )
    category_id = serializers.IntegerField(required=False, allow_null=True)
    publisher = serializers.CharField(max_length=180, allow_blank=True, required=False, default="")
    published_year = serializers.IntegerField(
        required=False, allow_null=True, min_value=1000, max_value=2200
    )
    language = serializers.CharField(max_length=40, required=False, default="English")
    page_count = serializers.IntegerField(required=False, allow_null=True, min_value=1)
    description = serializers.CharField(allow_blank=True, required=False, default="")
    cover_url = serializers.URLField(max_length=500, allow_blank=True, required=False, default="")

    def validate_isbn(self, value: str) -> str:
        from django.core.exceptions import ValidationError as DjangoValidationError

        from domains.catalog.validators import validate_isbn

        isbn = normalise_isbn(value)
        try:
            validate_isbn(isbn)
        except DjangoValidationError as exc:
            raise serializers.ValidationError(list(exc.messages)) from exc
        return isbn


class BookUpdateRequest(BookCreateRequest):
    """Same field set; every field optional so ``PATCH`` behaves."""

    def __init__(self, *args, **kwargs):
        kwargs["partial"] = True
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.required = False
