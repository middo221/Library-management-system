from django.db import models
from django.utils import timezone
from django.utils.text import slugify

from domains.catalog.validators import validate_isbn
from domains.common.models import TimeStampedModel


class Author(TimeStampedModel):
    name = models.CharField(max_length=180, db_index=True)
    bio = models.TextField(blank=True)
    birth_year = models.PositiveIntegerField(null=True, blank=True)
    death_year = models.PositiveIntegerField(null=True, blank=True)

    class Meta:
        ordering = ("name",)

    def __str__(self) -> str:
        return self.name


class Category(TimeStampedModel):
    name = models.CharField(max_length=120, unique=True)
    slug = models.SlugField(max_length=140, unique=True, blank=True)
    description = models.TextField(blank=True)

    class Meta:
        ordering = ("name",)
        verbose_name_plural = "categories"

    def __str__(self) -> str:
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)[:140]
        super().save(*args, **kwargs)


class Book(TimeStampedModel):
    """The bibliographic record. Nothing here is a physical object — see ``BookCopy``."""

    isbn = models.CharField(max_length=13, unique=True, db_index=True, validators=[validate_isbn])
    title = models.CharField(max_length=300, db_index=True)
    subtitle = models.CharField(max_length=300, blank=True)

    authors = models.ManyToManyField(Author, related_name="books", blank=True)
    category = models.ForeignKey(
        Category, on_delete=models.SET_NULL, null=True, blank=True, related_name="books"
    )

    publisher = models.CharField(max_length=180, blank=True)
    published_year = models.PositiveIntegerField(null=True, blank=True, db_index=True)
    language = models.CharField(max_length=40, default="English", db_index=True)
    page_count = models.PositiveIntegerField(null=True, blank=True)

    description = models.TextField(blank=True)
    cover_url = models.URLField(max_length=500, blank=True)

    class Meta:
        ordering = ("title",)
        indexes = [models.Index(fields=("title", "published_year"))]

    def __str__(self) -> str:
        return self.title


class BookCopy(TimeStampedModel):
    """A physical object on a shelf. Loans attach here, never to ``Book``."""

    class Status(models.TextChoices):
        AVAILABLE = "AVAILABLE", "Available"
        ON_LOAN = "ON_LOAN", "On loan"
        RESERVED = "RESERVED", "Reserved"
        LOST = "LOST", "Lost"
        DAMAGED = "DAMAGED", "Damaged"
        WITHDRAWN = "WITHDRAWN", "Withdrawn"

    #: Statuses that count towards a title's availability for borrowing.
    LENDABLE_STATUSES = (Status.AVAILABLE,)
    #: Statuses that mean the copy still belongs to the collection.
    IN_COLLECTION_STATUSES = (Status.AVAILABLE, Status.ON_LOAN, Status.RESERVED, Status.DAMAGED)

    book = models.ForeignKey(Book, on_delete=models.CASCADE, related_name="copies")
    barcode = models.CharField(max_length=32, unique=True, db_index=True)
    call_number = models.CharField(max_length=40, blank=True, db_index=True)
    status = models.CharField(
        max_length=16, choices=Status.choices, default=Status.AVAILABLE, db_index=True
    )
    acquired_on = models.DateField(default=timezone.localdate)
    condition_note = models.CharField(max_length=255, blank=True)
    replacement_cost = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)

    class Meta:
        ordering = ("book__title", "barcode")
        verbose_name_plural = "book copies"

    def __str__(self) -> str:
        return f"{self.barcode} — {self.book.title}"

    @property
    def is_available(self) -> bool:
        return self.status == self.Status.AVAILABLE


#: Module-level alias so ``SPECTACULAR_SETTINGS["ENUM_NAME_OVERRIDES"]`` can import it.
COPY_STATUS_CHOICES = BookCopy.Status.choices
