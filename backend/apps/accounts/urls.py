"""Routes de l'API comptes (phase 5)."""

from django.urls import path

from .views import DesinscriptionView, InscriptionView, StatutInscriptionView

app_name = "accounts"

urlpatterns = [
    path("inscriptions/", InscriptionView.as_view(), name="inscriptions"),
    path("inscriptions/statut/", StatutInscriptionView.as_view(), name="statut"),
    path("desinscription/", DesinscriptionView.as_view(), name="desinscription"),
]
