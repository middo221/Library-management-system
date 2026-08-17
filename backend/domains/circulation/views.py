"""Circulation views.

Ownership rule: a member asking for someone else's record gets **403**, not 404. The id is
already known to them (it came from somewhere), so hiding existence buys nothing and a
truthful status is easier to act on. Recorded in ``docs/decisions.md``.
"""

from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from domains.accounts.selectors import get_member
from domains.catalog.exceptions import BookNotFound
from domains.catalog.models import Book
from domains.circulation import selectors, services
from domains.circulation.dtos import (
    CheckoutRequest,
    DashboardStatsResponse,
    FineResponse,
    LoanResponse,
    ReservationCreateRequest,
    ReservationResponse,
    ReturnResponse,
    WaiveFineRequest,
)
from domains.circulation.exceptions import FineNotFound, LoanNotFound, ReservationNotFound
from domains.common.exceptions import PermissionDeniedError, ValidationError
from domains.common.pagination import StandardPagination
from domains.common.permissions import IsLibrarian


def _int_param(value: str | None) -> int | None:
    try:
        return int(value) if value not in (None, "") else None
    except ValueError:
        return None


def _assert_can_view(record, user) -> None:
    if user.is_librarian:
        return
    if record.owner_user != user:
        raise PermissionDeniedError("You may only view your own records.")


class LoanListView(APIView):
    permission_classes = [IsLibrarian]

    @extend_schema(
        parameters=[
            OpenApiParameter("status", str, enum=["active", "overdue", "returned"]),
            OpenApiParameter("member", int),
            OpenApiParameter("book", int),
            OpenApiParameter(
                "search", str, description="Barcode, title, email or membership number"
            ),
        ],
        responses={200: LoanResponse(many=True)},
        tags=["circulation"],
    )
    def get(self, request: Request) -> Response:
        queryset = selectors.list_loans(
            status=request.query_params.get("status", ""),
            member=_int_param(request.query_params.get("member")),
            book=_int_param(request.query_params.get("book")),
            search=request.query_params.get("search", "").strip(),
        )
        paginator = StandardPagination()
        page = paginator.paginate_queryset(queryset, request, view=self)
        return paginator.get_paginated_response(LoanResponse(page, many=True).data)

    @extend_schema(request=CheckoutRequest, responses={201: LoanResponse}, tags=["circulation"])
    def post(self, request: Request) -> Response:
        payload = CheckoutRequest(data=request.data)
        payload.is_valid(raise_exception=True)

        member = get_member(member_id=payload.validated_data["member_id"])
        if member is None:
            raise ValidationError(
                "No member with that id exists.", details={"member_id": "Unknown member."}
            )

        loan = services.checkout(
            barcode=payload.validated_data["barcode"], member=member, librarian=request.user
        )
        loan = selectors.get_loan(loan_id=loan.id)
        return Response(LoanResponse(loan).data, status=status.HTTP_201_CREATED)


class LoanDetailView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(responses={200: LoanResponse}, tags=["circulation"])
    def get(self, request: Request, loan_id: int) -> Response:
        loan = selectors.get_loan(loan_id=loan_id)
        if loan is None:
            raise LoanNotFound()
        _assert_can_view(loan, request.user)
        return Response(LoanResponse(loan).data)


class LoanReturnView(APIView):
    permission_classes = [IsLibrarian]

    @extend_schema(request=None, responses={200: ReturnResponse}, tags=["circulation"])
    def post(self, request: Request, loan_id: int) -> Response:
        loan = selectors.get_loan(loan_id=loan_id)
        if loan is None:
            raise LoanNotFound()

        result = services.return_loan(loan=loan, librarian=request.user)
        result["loan"] = selectors.get_loan(loan_id=loan.id)
        return Response(ReturnResponse(result).data)


class LoanRenewView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(request=None, responses={200: LoanResponse}, tags=["circulation"])
    def post(self, request: Request, loan_id: int) -> Response:
        loan = selectors.get_loan(loan_id=loan_id)
        if loan is None:
            raise LoanNotFound()
        _assert_can_view(loan, request.user)

        services.renew_loan(loan=loan, actor=request.user)
        return Response(LoanResponse(selectors.get_loan(loan_id=loan_id)).data)


class ReservationListView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        parameters=[
            OpenApiParameter(
                "status",
                str,
                enum=["active", "PENDING", "READY", "FULFILLED", "CANCELLED", "EXPIRED"],
            ),
            OpenApiParameter("book", int),
            OpenApiParameter("member", int, description="Librarians only"),
        ],
        responses={200: ReservationResponse(many=True)},
        tags=["circulation"],
    )
    def get(self, request: Request) -> Response:
        member_filter = _int_param(request.query_params.get("member"))
        if not request.user.is_librarian:
            member_filter = request.user.id

        queryset = selectors.list_reservations(
            member=member_filter,
            book=_int_param(request.query_params.get("book")),
            status=request.query_params.get("status", ""),
        )
        paginator = StandardPagination()
        page = paginator.paginate_queryset(queryset, request, view=self)
        return paginator.get_paginated_response(ReservationResponse(page, many=True).data)

    @extend_schema(
        request=ReservationCreateRequest, responses={201: ReservationResponse}, tags=["circulation"]
    )
    def post(self, request: Request) -> Response:
        payload = ReservationCreateRequest(data=request.data)
        payload.is_valid(raise_exception=True)

        member = request.user
        requested_member_id = payload.validated_data.get("member_id")
        if requested_member_id and requested_member_id != request.user.id:
            if not request.user.is_librarian:
                raise PermissionDeniedError("You may only reserve titles for yourself.")
            member = get_member(member_id=requested_member_id)
            if member is None:
                raise ValidationError(
                    "No member with that id exists.", details={"member_id": "Unknown member."}
                )

        book = Book.objects.filter(pk=payload.validated_data["book_id"]).first()
        if book is None:
            raise BookNotFound()

        reservation = services.reserve(book=book, member=member)
        reservation = selectors.get_reservation(reservation_id=reservation.id)
        return Response(ReservationResponse(reservation).data, status=status.HTTP_201_CREATED)


class ReservationCancelView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(request=None, responses={200: ReservationResponse}, tags=["circulation"])
    def post(self, request: Request, reservation_id: int) -> Response:
        reservation = selectors.get_reservation(reservation_id=reservation_id)
        if reservation is None:
            raise ReservationNotFound()
        _assert_can_view(reservation, request.user)

        services.cancel_reservation(reservation=reservation, actor=request.user)
        return Response(
            ReservationResponse(selectors.get_reservation(reservation_id=reservation_id)).data
        )


class ReservationFulfilView(APIView):
    permission_classes = [IsLibrarian]

    @extend_schema(request=None, responses={201: LoanResponse}, tags=["circulation"])
    def post(self, request: Request, reservation_id: int) -> Response:
        reservation = selectors.get_reservation(reservation_id=reservation_id)
        if reservation is None:
            raise ReservationNotFound()

        loan = services.fulfil_reservation(reservation=reservation, librarian=request.user)
        return Response(
            LoanResponse(selectors.get_loan(loan_id=loan.id)).data, status=status.HTTP_201_CREATED
        )


class FineListView(APIView):
    permission_classes = [IsLibrarian]

    @extend_schema(
        parameters=[
            OpenApiParameter("status", str, enum=["outstanding", "paid", "waived"]),
            OpenApiParameter("member", int),
        ],
        responses={200: FineResponse(many=True)},
        tags=["circulation"],
    )
    def get(self, request: Request) -> Response:
        queryset = selectors.list_fines(
            member=_int_param(request.query_params.get("member")),
            status=request.query_params.get("status", ""),
        )
        paginator = StandardPagination()
        page = paginator.paginate_queryset(queryset, request, view=self)
        return paginator.get_paginated_response(FineResponse(page, many=True).data)


class FinePayView(APIView):
    permission_classes = [IsLibrarian]

    @extend_schema(request=None, responses={200: FineResponse}, tags=["circulation"])
    def post(self, request: Request, fine_id: int) -> Response:
        fine = selectors.get_fine(fine_id=fine_id)
        if fine is None:
            raise FineNotFound()

        fine = services.pay_fine(fine=fine, librarian=request.user)
        return Response(FineResponse(fine).data)


class FineWaiveView(APIView):
    permission_classes = [IsLibrarian]

    @extend_schema(request=WaiveFineRequest, responses={200: FineResponse}, tags=["circulation"])
    def post(self, request: Request, fine_id: int) -> Response:
        fine = selectors.get_fine(fine_id=fine_id)
        if fine is None:
            raise FineNotFound()

        payload = WaiveFineRequest(data=request.data)
        payload.is_valid(raise_exception=True)

        fine = services.waive_fine(
            fine=fine, librarian=request.user, reason=payload.validated_data["reason"]
        )
        return Response(FineResponse(fine).data)


# --------------------------------------------------------------------------------------
# "My shelf" — the member's own view of circulation
# --------------------------------------------------------------------------------------


class MyLoansView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        parameters=[OpenApiParameter("status", str, enum=["active", "overdue", "returned"])],
        responses={200: LoanResponse(many=True)},
        tags=["members"],
    )
    def get(self, request: Request) -> Response:
        queryset = selectors.list_loans(
            member=request.user.id, status=request.query_params.get("status", "")
        )
        paginator = StandardPagination()
        page = paginator.paginate_queryset(queryset, request, view=self)
        return paginator.get_paginated_response(LoanResponse(page, many=True).data)


class MyReservationsView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(responses={200: ReservationResponse(many=True)}, tags=["members"])
    def get(self, request: Request) -> Response:
        queryset = selectors.list_reservations(
            member=request.user.id, status=request.query_params.get("status", "")
        )
        paginator = StandardPagination()
        page = paginator.paginate_queryset(queryset, request, view=self)
        return paginator.get_paginated_response(ReservationResponse(page, many=True).data)


class MyFinesView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(responses={200: FineResponse(many=True)}, tags=["members"])
    def get(self, request: Request) -> Response:
        queryset = selectors.list_fines(
            member=request.user.id, status=request.query_params.get("status", "")
        )
        paginator = StandardPagination()
        page = paginator.paginate_queryset(queryset, request, view=self)
        return paginator.get_paginated_response(FineResponse(page, many=True).data)


class DashboardStatsView(APIView):
    permission_classes = [IsLibrarian]

    @extend_schema(responses={200: DashboardStatsResponse}, tags=["dashboard"])
    def get(self, request: Request) -> Response:
        return Response(DashboardStatsResponse(selectors.dashboard_stats()).data)
