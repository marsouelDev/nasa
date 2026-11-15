"""Vues REST de l'application rotations (comparaison des scénarios)."""

from __future__ import annotations

from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.data.views import zone_demandee
from apps.rotations import services
from apps.data.serializers import ZoneSerializer


class RotationView(APIView):
    """Comparaison des scénarios de rotation (S0, S1, S2) avec pondérations."""

    @extend_schema(
        parameters=[
            OpenApiParameter("zone", str, description="Identifiant de zone (défaut : bafia)."),
            OpenApiParameter(
                "priorites",
                str,
                description="Priorités séparées par des virgules (defaut : eau,sol,revenu,travail).",
            ),
            OpenApiParameter(
                "pondations",
                str,
                description="Poids par priorité sous la forme categorie=poids,categorie=poids (ex. eau=0.30).",
            ),
            OpenApiParameter(
                "pluie",
                float,
                description="Facteur de pluie personnalisé (ex. -0.3 pour une pluie de 30 % en moins).",
            ),
        ],
        responses={200: dict},
    )
    def get(self, request):
        zone = zone_demandee(request)
        priorites = [valeur for valeur in (request.query_params.get("priorites") or "").split(",") if valeur]
        pondations: dict = {}
        parametre_pondations = request.query_params.get("pondations")
        if parametre_pondations:
            for partie in parametre_pondations.split(","):
                if "=" not in partie:
                    continue
                categorie, valeur = partie.split("=", 1)
                try:
                    pondations[categorie.strip()] = float(valeur.strip())
                except ValueError:
                    continue
        parametre_pluie = request.query_params.get("pluie")
        pluie_facteur: float | None = None
        if parametre_pluie not in (None, ""):
            try:
                pluie_facteur = float(parametre_pluie)
            except ValueError:
                pluie_facteur = None
        fixtures = services.charger_fixtures()
        reponse = services.construire_reponse(
            fixtures=fixtures,
            zone=ZoneSerializer(zone).data,
            priorites=priorites or None,
            pondations=pondations or None,
            pluie_facteur=pluie_facteur,
        )
        return Response(reponse)
