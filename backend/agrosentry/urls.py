"""Routage principal d'AgroSentry."""

from django.contrib import admin
from django.http import JsonResponse
from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

admin.site.site_header = "Administration AgroSentry"
admin.site.site_title = "AgroSentry"
admin.site.index_title = "Gestion des zones, données et campagnes"


def health(request):
    """Vérification de disponibilité, sans accès à la base de données."""
    return JsonResponse({"status": "ok"})


urlpatterns = [
    path("health", health, name="health"),
    path("admin/", admin.site.urls),
    path("api/", include("apps.accounts.urls")),
    path("api/", include("apps.data.urls")),
    path("api/rotations/", include("apps.rotations.urls")),
    path("api/sms/", include("apps.sms.urls")),
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
]