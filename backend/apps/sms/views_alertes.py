"""Endpoint déclenchant l'envoi des alertes de risque (phase 5)."""

from __future__ import annotations

from drf_spectacular.utils import extend_schema
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.sms.tasks import envoyer_alertes_risque


class AlertesView(APIView):
    """Déclenche la tâche Celery d'envoi des alertes de risque.

    En mode eager, la tâche s'exécute immédiatement et le résumé est renvoyé.
    """

    permission_classes = [AllowAny]

    @extend_schema(request=None, responses={200: dict})
    def post(self, request):
        zone_slug = (request.query_params.get("zone") or "").strip()[:60] or None
        resultat = envoyer_alertes_risque.delay(zone_slug)
        return Response(
            {
                "task_id": str(resultat.id) if hasattr(resultat, "id") else "eager",
                "simulation": True,
                "zone": zone_slug,
                "resultat": resultat,
            },
            status=200,
        )
