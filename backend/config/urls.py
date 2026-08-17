from django.conf import settings
from django.contrib import admin
from django.urls import include, path, re_path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

from domains.common.views import api_not_found, health, spa

api_v1 = [
    path("auth/", include("domains.accounts.urls_auth")),
    path("", include("domains.accounts.urls")),
    path("", include("domains.catalog.urls")),
    path("", include("domains.circulation.urls")),
]

urlpatterns = [
    path("admin/", admin.site.urls),
    path("healthz", health, name="health"),
    path("api/v1/", include((api_v1, "v1"))),
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
]

if settings.DEBUG:  # pragma: no cover - developer convenience
    urlpatterns += [path("api-auth/", include("rest_framework.urls"))]

# Must stay last. Unknown API paths keep the error envelope; everything else that is not the
# admin or a static file belongs to the client-side router.
urlpatterns += [
    re_path(r"^api/.*$", api_not_found, name="api-not-found"),
    re_path(r"^(?!api/|admin/|static/|healthz).*$", spa, name="spa"),
]
