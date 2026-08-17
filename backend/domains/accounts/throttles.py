from rest_framework.throttling import AnonRateThrottle


class AuthEndpointThrottle(AnonRateThrottle):
    """Tighter bucket for credential-handling endpoints."""

    scope = "auth"
