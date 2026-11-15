"""Routes de l'API SMS (phase 5)."""

from django.urls import path

from .views import ApercuSMSView, JournalSMSView, SimulerSMSView
from .views_alertes import AlertesView
from .views_ussd import SimulerUssdView, UssdWebhookView

app_name = "sms"

urlpatterns = [
    path("apercu/", ApercuSMSView.as_view(), name="apercu"),
    path("alertes/", AlertesView.as_view(), name="alertes"),
    path("simuler/", SimulerSMSView.as_view(), name="simuler"),
    path("journal/", JournalSMSView.as_view(), name="journal"),
    path("ussd/webhook/", UssdWebhookView.as_view(), name="ussd-webhook"),
    path("ussd/simuler/", SimulerUssdView.as_view(), name="ussd-simuler"),
]
