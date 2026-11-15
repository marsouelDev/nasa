"""Routes de l'API data."""

from django.urls import include, path
from rest_framework.routers import SimpleRouter

from .views import (
    ApiIndexView,
    CalendrierSemisView,
    PluieView,
    PointView,
    RisquesView,
    TendancesView,
    ZoneViewSet,
)

router = SimpleRouter()
router.register("zones", ZoneViewSet, basename="zone")

urlpatterns = [
    path("", ApiIndexView.as_view(), name="api-index"),
    path("", include(router.urls)),
    path("pluie/", PluieView.as_view(), name="pluie"),
    path("pluie/tendances/", TendancesView.as_view(), name="pluie-tendances"),
    path("risques/", RisquesView.as_view(), name="risques"),
    path("calendrier-semis/", CalendrierSemisView.as_view(), name="calendrier-semis"),
    path("point/", PointView.as_view(), name="point"),
]
