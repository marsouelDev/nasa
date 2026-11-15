"""Endpoints USSD simulés (phase 5) : webhook Africa's Talking et simulateur."""

from __future__ import annotations

from datetime import date

from django.http import HttpResponse
from drf_spectacular.utils import extend_schema
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.data.services import season
from apps.data.views import evaluer_risque, saison, zone_demandee
from apps.sms import ussd
from apps.sms.services import simulation_active


def _contexte_ussd(request) -> tuple:
    """Résout la zone et les données nécessaires au menu USSD."""
    zone = zone_demandee(request)
    risque = evaluer_risque(zone)

    lignes = list(
        zone.weather.order_by("-date")[:30].values_list("precip_mm", flat=True)
    )
    valeurs = [v for v in lignes if v is not None]
    pluie_30j = round(sum(valeurs), 1) if valeurs else None

    _, stats = saison(zone)
    derniere = zone.weather.order_by("-date").values_list("date", flat=True).first()
    annee = (derniere.year + 1) if derniere else date.today().year + 1
    fenetre = season.fenetre_pour_annee(stats, annee)

    return zone, risque, pluie_30j, fenetre


def _texte_saisi(request) -> str | None:
    """Récupère le texte USSD depuis JSON, formulaire ou query string."""
    if hasattr(request.data, "get"):
        valeur = request.data.get("text")
        if valeur is not None:
            return str(valeur)
    valeur = request.query_params.get("text")
    return str(valeur) if valeur is not None else None


class UssdWebhookView(APIView):
    """Webhook USSD compatible Africa's Talking (aucun appel réel en phase 5).

    Retourne la réponse USSD (`CON`/`END`) en `text/plain`, comme le ferait la
    plateforme. Aucun SMS n'est envoyé : c'est la réponse qui est servie.
    """

    permission_classes = [AllowAny]

    @extend_schema(request=None, responses={200: str})
    def post(self, request):
        zone, risque, pluie_30j, fenetre = _contexte_ussd(request)
        reponse = ussd.traiter(
            _texte_saisi(request),
            zone_nom=zone.nom,
            risque=risque,
            fenetre_semis=fenetre,
            pluie_30j=pluie_30j,
        )
        return HttpResponse(reponse, content_type="text/plain; charset=utf-8")


class SimulerUssdView(APIView):
    """Simule une session USSD et renvoie la réponse en JSON (console)."""

    permission_classes = [AllowAny]

    @extend_schema(request=None, responses={200: dict})
    def post(self, request):
        zone, risque, pluie_30j, fenetre = _contexte_ussd(request)
        reponse = ussd.traiter(
            _texte_saisi(request),
            zone_nom=zone.nom,
            risque=risque,
            fenetre_semis=fenetre,
            pluie_30j=pluie_30j,
        )
        return Response(
            {
                "reponse": reponse,
                "longueur": len(reponse),
                "longueur_max": ussd.LONGUEUR_MAX_USSD,
                "simulation": simulation_active(),
                "zone": {"slug": zone.slug, "nom": zone.nom},
                "source": "USSD simulé (démonstration, aucun réseau mobile)",
            }
        )
