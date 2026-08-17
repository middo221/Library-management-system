from django.urls import path

from domains.catalog import views

urlpatterns = [
    path("books", views.BookListView.as_view(), name="book-list"),
    path("books/<int:book_id>", views.BookDetailView.as_view(), name="book-detail"),
    path("books/<int:book_id>/copies", views.BookCopyListView.as_view(), name="book-copy-list"),
    path("copies/<int:copy_id>", views.CopyDetailView.as_view(), name="copy-detail"),
    path("authors", views.AuthorListView.as_view(), name="author-list"),
    path("authors/<int:author_id>", views.AuthorDetailView.as_view(), name="author-detail"),
    path("categories", views.CategoryListView.as_view(), name="category-list"),
    path(
        "categories/<int:category_id>", views.CategoryDetailView.as_view(), name="category-detail"
    ),
]
