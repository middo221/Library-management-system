"""Catalogue views. Reading is open to any authenticated user; writing is librarian-only."""

from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from domains.catalog import selectors, services
from domains.catalog.dtos import (
    AuthorResponse,
    AuthorWriteRequest,
    BookCreateRequest,
    BookListItemResponse,
    BookResponse,
    BookUpdateRequest,
    CategoryResponse,
    CategoryWriteRequest,
    CopyCreateRequest,
    CopyResponse,
    CopyUpdateRequest,
)
from domains.catalog.exceptions import AuthorNotFound, BookNotFound, CategoryNotFound, CopyNotFound
from domains.common.pagination import StandardPagination
from domains.common.permissions import IsLibrarian, IsLibrarianOrReadOnly


def _bool_param(value: str | None) -> bool | None:
    if value is None or value == "":
        return None
    return value.lower() in {"true", "1", "yes"}


def _int_param(value: str | None) -> int | None:
    try:
        return int(value) if value not in (None, "") else None
    except ValueError:
        return None


class BookListView(APIView):
    permission_classes = [IsLibrarianOrReadOnly]

    @extend_schema(
        parameters=[
            OpenApiParameter("search", str, description="Title, subtitle, ISBN or author name"),
            OpenApiParameter("category", int),
            OpenApiParameter("author", int),
            OpenApiParameter("language", str),
            OpenApiParameter("available", bool),
            OpenApiParameter(
                "ordering",
                str,
                enum=[
                    "title",
                    "-title",
                    "published_year",
                    "-published_year",
                    "created_at",
                    "-created_at",
                ],
            ),
        ],
        responses={200: BookListItemResponse(many=True)},
        tags=["catalog"],
    )
    def get(self, request: Request) -> Response:
        queryset = selectors.list_books(
            search=request.query_params.get("search", "").strip(),
            category=_int_param(request.query_params.get("category")),
            author=_int_param(request.query_params.get("author")),
            language=request.query_params.get("language", "").strip(),
            available=_bool_param(request.query_params.get("available")),
            ordering=request.query_params.get("ordering", "title"),
        )

        paginator = StandardPagination()
        page = paginator.paginate_queryset(queryset, request, view=self)
        return paginator.get_paginated_response(BookListItemResponse(page, many=True).data)

    @extend_schema(request=BookCreateRequest, responses={201: BookResponse}, tags=["catalog"])
    def post(self, request: Request) -> Response:
        payload = BookCreateRequest(data=request.data)
        payload.is_valid(raise_exception=True)

        book = services.create_book(data=payload.validated_data, actor=request.user)
        book = selectors.get_book(book_id=book.id)
        return Response(BookResponse(book).data, status=status.HTTP_201_CREATED)


class BookDetailView(APIView):
    permission_classes = [IsLibrarianOrReadOnly]

    def _get(self, book_id: int):
        book = selectors.get_book(book_id=book_id)
        if book is None:
            raise BookNotFound()
        return book

    @extend_schema(responses={200: BookResponse}, tags=["catalog"])
    def get(self, request: Request, book_id: int) -> Response:
        return Response(BookResponse(self._get(book_id)).data)

    @extend_schema(request=BookUpdateRequest, responses={200: BookResponse}, tags=["catalog"])
    def patch(self, request: Request, book_id: int) -> Response:
        book = self._get(book_id)
        payload = BookUpdateRequest(data=request.data)
        payload.is_valid(raise_exception=True)

        services.update_book(book=book, data=payload.validated_data, actor=request.user)
        return Response(BookResponse(self._get(book_id)).data)

    @extend_schema(responses={204: None}, tags=["catalog"])
    def delete(self, request: Request, book_id: int) -> Response:
        services.delete_book(book=self._get(book_id), actor=request.user)
        return Response(status=status.HTTP_204_NO_CONTENT)


class BookCopyListView(APIView):
    permission_classes = [IsLibrarianOrReadOnly]

    @extend_schema(responses={200: CopyResponse(many=True)}, tags=["catalog"])
    def get(self, request: Request, book_id: int) -> Response:
        if selectors.get_book(book_id=book_id) is None:
            raise BookNotFound()
        copies = selectors.list_copies(book_id=book_id)
        return Response(CopyResponse(copies, many=True).data)

    @extend_schema(request=CopyCreateRequest, responses={201: CopyResponse}, tags=["catalog"])
    def post(self, request: Request, book_id: int) -> Response:
        book = selectors.get_book(book_id=book_id)
        if book is None:
            raise BookNotFound()

        payload = CopyCreateRequest(data=request.data)
        payload.is_valid(raise_exception=True)

        copy = services.add_copy(book=book, data=payload.validated_data, actor=request.user)
        return Response(CopyResponse(copy).data, status=status.HTTP_201_CREATED)


class CopyDetailView(APIView):
    permission_classes = [IsLibrarian]

    def _get(self, copy_id: int):
        copy = selectors.get_copy(copy_id=copy_id)
        if copy is None:
            raise CopyNotFound()
        return copy

    @extend_schema(responses={200: CopyResponse}, tags=["catalog"])
    def get(self, request: Request, copy_id: int) -> Response:
        return Response(CopyResponse(self._get(copy_id)).data)

    @extend_schema(request=CopyUpdateRequest, responses={200: CopyResponse}, tags=["catalog"])
    def patch(self, request: Request, copy_id: int) -> Response:
        copy = self._get(copy_id)
        payload = CopyUpdateRequest(data=request.data, partial=True)
        payload.is_valid(raise_exception=True)

        copy = services.update_copy(copy=copy, data=payload.validated_data, actor=request.user)
        return Response(CopyResponse(copy).data)

    @extend_schema(responses={204: None}, tags=["catalog"])
    def delete(self, request: Request, copy_id: int) -> Response:
        services.delete_copy(copy=self._get(copy_id), actor=request.user)
        return Response(status=status.HTTP_204_NO_CONTENT)


class AuthorListView(APIView):
    permission_classes = [IsLibrarianOrReadOnly]

    @extend_schema(
        parameters=[OpenApiParameter("search", str)],
        responses={200: AuthorResponse(many=True)},
        tags=["catalog"],
    )
    def get(self, request: Request) -> Response:
        queryset = selectors.list_authors(search=request.query_params.get("search", "").strip())
        paginator = StandardPagination()
        page = paginator.paginate_queryset(queryset, request, view=self)
        return paginator.get_paginated_response(AuthorResponse(page, many=True).data)

    @extend_schema(request=AuthorWriteRequest, responses={201: AuthorResponse}, tags=["catalog"])
    def post(self, request: Request) -> Response:
        payload = AuthorWriteRequest(data=request.data)
        payload.is_valid(raise_exception=True)

        author = services.create_author(data=payload.validated_data, actor=request.user)
        return Response(AuthorResponse(author).data, status=status.HTTP_201_CREATED)


class AuthorDetailView(APIView):
    permission_classes = [IsLibrarianOrReadOnly]

    def _get(self, author_id: int):
        author = selectors.get_author(author_id=author_id)
        if author is None:
            raise AuthorNotFound()
        return author

    @extend_schema(responses={200: AuthorResponse}, tags=["catalog"])
    def get(self, request: Request, author_id: int) -> Response:
        return Response(AuthorResponse(self._get(author_id)).data)

    @extend_schema(request=AuthorWriteRequest, responses={200: AuthorResponse}, tags=["catalog"])
    def patch(self, request: Request, author_id: int) -> Response:
        author = self._get(author_id)
        payload = AuthorWriteRequest(data=request.data, partial=True)
        payload.is_valid(raise_exception=True)

        author = services.update_author(
            author=author, data=payload.validated_data, actor=request.user
        )
        return Response(AuthorResponse(author).data)

    @extend_schema(responses={204: None}, tags=["catalog"])
    def delete(self, request: Request, author_id: int) -> Response:
        services.delete_author(author=self._get(author_id), actor=request.user)
        return Response(status=status.HTTP_204_NO_CONTENT)


class CategoryListView(APIView):
    permission_classes = [IsLibrarianOrReadOnly]

    @extend_schema(responses={200: CategoryResponse(many=True)}, tags=["catalog"])
    def get(self, request: Request) -> Response:
        return Response(CategoryResponse(selectors.list_categories(), many=True).data)

    @extend_schema(
        request=CategoryWriteRequest, responses={201: CategoryResponse}, tags=["catalog"]
    )
    def post(self, request: Request) -> Response:
        payload = CategoryWriteRequest(data=request.data)
        payload.is_valid(raise_exception=True)

        category = services.create_category(data=payload.validated_data, actor=request.user)
        return Response(CategoryResponse(category).data, status=status.HTTP_201_CREATED)


class CategoryDetailView(APIView):
    permission_classes = [IsLibrarianOrReadOnly]

    def _get(self, category_id: int):
        category = selectors.get_category(category_id=category_id)
        if category is None:
            raise CategoryNotFound()
        return category

    @extend_schema(responses={200: CategoryResponse}, tags=["catalog"])
    def get(self, request: Request, category_id: int) -> Response:
        return Response(CategoryResponse(self._get(category_id)).data)

    @extend_schema(
        request=CategoryWriteRequest, responses={200: CategoryResponse}, tags=["catalog"]
    )
    def patch(self, request: Request, category_id: int) -> Response:
        category = self._get(category_id)
        payload = CategoryWriteRequest(data=request.data, partial=True)
        payload.is_valid(raise_exception=True)

        category = services.update_category(
            category=category, data=payload.validated_data, actor=request.user
        )
        return Response(CategoryResponse(category).data)

    @extend_schema(responses={204: None}, tags=["catalog"])
    def delete(self, request: Request, category_id: int) -> Response:
        services.delete_category(category=self._get(category_id), actor=request.user)
        return Response(status=status.HTTP_204_NO_CONTENT)
