"""Routes de l'API SMS (phase 5)."""

from django.urls import path

from .views import ApercuSMSView, JournalSMSView, SimulerSMSView

app_name = "sms"

urlpatterns = [
    path("apercu/", ApercuSMSView.as_view(), name="apercu"),
    path("simuler/", SimulerSMSView.as_view(), name="simuler"),
    path("journal/", JournalSMSView.as_view(), name="journal"),
]
