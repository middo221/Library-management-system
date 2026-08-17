from django.conf import settings
from django.http import HttpRequest, HttpResponse, JsonResponse


def health(_request: HttpRequest) -> JsonResponse:
    """Unauthenticated liveness probe for container orchestration."""
    return JsonResponse({"status": "ok"})


def api_not_found(_request: HttpRequest) -> JsonResponse:
    """Unknown API paths answer in the same envelope as everything else."""
    return JsonResponse(
        {
            "error": {
                "code": "NOT_FOUND",
                "message": "No such endpoint. See /api/docs for the API surface.",
                "details": {},
            }
        },
        status=404,
    )


def spa(_request: HttpRequest) -> HttpResponse:
    """Hand any non-API path to the client-side router.

    WhiteNoise has already answered anything that exists on disk, so reaching here means the
    path belongs to React Router — including a hard refresh on a deep link.
    """
    index = settings.FRONTEND_DIST / "index.html"
    if not index.is_file():
        return JsonResponse(
            {
                "error": {
                    "code": "NOT_FOUND",
                    "message": (
                        "No frontend build is present in this container. The API is at /api/v1 "
                        "and the docs at /api/docs."
                    ),
                    "details": {},
                }
            },
            status=404,
        )
    return HttpResponse(index.read_bytes(), content_type="text/html")
