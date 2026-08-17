from django.contrib import admin

from domains.catalog.models import Author, Book, BookCopy, Category


class BookCopyInline(admin.TabularInline):
    model = BookCopy
    extra = 0


@admin.register(Book)
class BookAdmin(admin.ModelAdmin):
    list_display = ("title", "isbn", "category", "published_year", "language")
    list_filter = ("language", "category")
    search_fields = ("title", "subtitle", "isbn")
    filter_horizontal = ("authors",)
    inlines = [BookCopyInline]


@admin.register(BookCopy)
class BookCopyAdmin(admin.ModelAdmin):
    list_display = ("barcode", "book", "call_number", "status")
    list_filter = ("status",)
    search_fields = ("barcode", "call_number", "book__title")


@admin.register(Author)
class AuthorAdmin(admin.ModelAdmin):
    list_display = ("name", "birth_year", "death_year")
    search_fields = ("name",)


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "slug")
    search_fields = ("name",)
    prepopulated_fields = {"slug": ("name",)}
