"""Routes de l'API rotations."""

from django.urls import path

from .views import RotationView

app_name = "rotations"

urlpatterns = [
    path("", RotationView.as_view(), name="liste"),
]
