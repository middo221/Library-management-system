"""Auth and member views.

Views do three things: validate with a request DTO, call a service or selector, serialise
with a response DTO. There is no ORM access in this module.
"""

from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from domains.accounts import selectors, services
from domains.accounts.dtos import (
    ChangePasswordRequest,
    LoginRequest,
    LogoutRequest,
    MemberListItemResponse,
    MemberUpdateRequest,
    RefreshRequest,
    RegisterRequest,
    TokenResponse,
    UpdateMeRequest,
    UserResponse,
)
from domains.accounts.exceptions import NotAMember
from domains.accounts.throttles import AuthEndpointThrottle
from domains.accounts.tokens import issue_tokens, revoke_refresh_token, rotate_tokens
from domains.common.dtos import MessageResponse
from domains.common.pagination import StandardPagination
from domains.common.permissions import IsLibrarian


class RegisterView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [AuthEndpointThrottle]

    @extend_schema(request=RegisterRequest, responses={201: TokenResponse}, tags=["auth"])
    def post(self, request: Request) -> Response:
        payload = RegisterRequest(data=request.data)
        payload.is_valid(raise_exception=True)

        user = services.register_member(**payload.validated_data)
        tokens = issue_tokens(user)

        body = {**tokens, "user": user}
        return Response(TokenResponse(body).data, status=status.HTTP_201_CREATED)


class LoginView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [AuthEndpointThrottle]

    @extend_schema(request=LoginRequest, responses={200: TokenResponse}, tags=["auth"])
    def post(self, request: Request) -> Response:
        payload = LoginRequest(data=request.data)
        payload.is_valid(raise_exception=True)

        user = services.authenticate_user(**payload.validated_data)
        tokens = issue_tokens(user)

        body = {**tokens, "user": user}
        return Response(TokenResponse(body).data)


class RefreshView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [AuthEndpointThrottle]

    @extend_schema(request=RefreshRequest, responses={200: RefreshRequest}, tags=["auth"])
    def post(self, request: Request) -> Response:
        payload = RefreshRequest(data=request.data)
        payload.is_valid(raise_exception=True)

        tokens = rotate_tokens(payload.validated_data["refresh"])
        return Response(tokens)


class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(request=LogoutRequest, responses={200: MessageResponse}, tags=["auth"])
    def post(self, request: Request) -> Response:
        payload = LogoutRequest(data=request.data)
        payload.is_valid(raise_exception=True)

        revoke_refresh_token(payload.validated_data["refresh"])
        return Response(MessageResponse({"detail": "Signed out."}).data)


class MeView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(responses={200: UserResponse}, tags=["auth"])
    def get(self, request: Request) -> Response:
        return Response(UserResponse(request.user).data)

    @extend_schema(request=UpdateMeRequest, responses={200: UserResponse}, tags=["auth"])
    def patch(self, request: Request) -> Response:
        payload = UpdateMeRequest(data=request.data, partial=True)
        payload.is_valid(raise_exception=True)

        user = services.update_own_profile(user=request.user, data=payload.validated_data)
        return Response(UserResponse(user).data)


class ChangePasswordView(APIView):
    permission_classes = [IsAuthenticated]
    throttle_classes = [AuthEndpointThrottle]

    @extend_schema(request=ChangePasswordRequest, responses={200: MessageResponse}, tags=["auth"])
    def post(self, request: Request) -> Response:
        payload = ChangePasswordRequest(data=request.data)
        payload.is_valid(raise_exception=True)

        services.change_password(user=request.user, **payload.validated_data)
        return Response(MessageResponse({"detail": "Password changed."}).data)


class MemberListView(APIView):
    permission_classes = [IsLibrarian]

    @extend_schema(
        parameters=[
            OpenApiParameter("search", str, description="Email, name or membership number"),
            OpenApiParameter("is_suspended", bool),
        ],
        responses={200: MemberListItemResponse(many=True)},
        tags=["members"],
    )
    def get(self, request: Request) -> Response:
        suspended = request.query_params.get("is_suspended")
        queryset = selectors.members_queryset(
            search=request.query_params.get("search", "").strip(),
            is_suspended=None if suspended is None else suspended.lower() == "true",
        )

        paginator = StandardPagination()
        page = paginator.paginate_queryset(queryset, request, view=self)
        return paginator.get_paginated_response(MemberListItemResponse(page, many=True).data)


class MemberDetailView(APIView):
    permission_classes = [IsLibrarian]

    @extend_schema(responses={200: UserResponse}, tags=["members"])
    def get(self, request: Request, member_id: int) -> Response:
        member = selectors.get_member(member_id=member_id)
        if member is None:
            raise NotAMember()
        return Response(UserResponse(member).data)

    @extend_schema(request=MemberUpdateRequest, responses={200: UserResponse}, tags=["members"])
    def patch(self, request: Request, member_id: int) -> Response:
        member = selectors.get_member(member_id=member_id)
        if member is None:
            raise NotAMember()

        payload = MemberUpdateRequest(data=request.data, partial=True)
        payload.is_valid(raise_exception=True)

        member = services.update_member(
            member=member, data=payload.validated_data, actor=request.user
        )
        return Response(UserResponse(member).data)
