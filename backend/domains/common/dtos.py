"""DTO helpers shared across domains."""

from rest_framework import serializers


class ErrorDetailResponse(serializers.Serializer):
    """Documents the single error envelope for the OpenAPI schema."""

    code = serializers.CharField()
    message = serializers.CharField()
    details = serializers.DictField(required=False)


class ErrorResponse(serializers.Serializer):
    error = ErrorDetailResponse()


class MessageResponse(serializers.Serializer):
    """For endpoints whose only useful answer is 'it worked'."""

    detail = serializers.CharField()
