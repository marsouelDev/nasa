"""Vues REST de l'application data (zones, pluie, risques, calendrier, point)."""

from __future__ import annotations

from datetime import date, timedelta

from django.conf import settings
from django.db.models import Max
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import viewsets
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Zone
from .serializers import ZoneSerializer
from .services import analytics, risk, season
from .utils import parse_date_param, parse_float_param, parse_int_param

from apps.ml import services as ml_services

SOURCE_NASA = "NASA POWER (données réelles, communauté AG)"
DUREE_MAX_SERIE_JOURS = 4000


def zone_demandee(request) -> Zone:
    """Zone passée en ?zone=slug, sinon la zone par défaut des settings."""
    slug = request.query_params.get("zone") or settings.DEFAULT_ZONE_SLUG
    zone = Zone.objects.filter(slug=slug, actif=True).first()
    if zone is None:
        disponibles = list(Zone.objects.filter(actif=True).values_list("slug", flat=True))
        raise NotFound(
            f"Zone « {slug} » inconnue. Zones disponibles : "
            f"{', '.join(disponibles) if disponibles else 'aucune'}."
        )
    return zone


def derniere_date(zone: Zone) -> date | None:
    return zone.weather.aggregate(derniere=Max("date"))["derniere"]


def saison(zone: Zone) -> tuple[dict[int, date], dict]:
    serie = zone.weather.order_by("date").values_list("date", "precip_mm")
    onsets = season.onset_dates(serie)
    return onsets, season.onset_statistics(onsets)


def evaluer_risque(zone: Zone) -> dict:
    """Risque de poche de sécheresse : Random Forest si entraîné, règle sinon.

    La phase 2 remplace la règle par le modèle ; tant que le modèle n'existe
    pas, on retombe sur la règle simple et on l'étiquette comme phase 1.
    """
    serie = list(
        zone.weather.order_by("date").values_list("date", "precip_mm", "tmax_c", "tmin_c")
    )
    artefact = ml_services.charger()
    if serie and artefact is not None:
        return ml_services.predire(artefact, serie)

    lignes_recentes = list(
        zone.weather.order_by("-date")[: risk.FENETRE_ANALYSE_JOURS].values_list("date", "precip_mm")
    )
    lignes_recentes.reverse()
    return risk.assess(lignes_recentes)


class ApiIndexView(APIView):
    """Point d'entrée de découverte de l'API."""

    @extend_schema(responses={200: dict})
    def get(self, request):
        return Response(
            {
                "application": "AgroSentry",
                "version": "1.0.0",
                "phase": "1 — backend Django",
                "documentation": request.build_absolute_uri("/api/docs/"),
                "schema": request.build_absolute_uri("/api/schema/"),
                "endpoints": {
                    "zones": "/api/zones/",
                    "pluie": "/api/pluie/?zone=bafia&debut=2025-01-01&fin=2025-12-31",
                    "tendances": "/api/pluie/tendances/?zone=bafia&annees_reference=10",
                    "risques": "/api/risques/?zone=bafia",
                    "calendrier_semis": "/api/calendrier-semis/?zone=bafia",
                    "point": "/api/point/?lat=4.75&lon=11.23",
                },
            }
        )


class ZoneViewSet(viewsets.ReadOnlyModelViewSet):
    """Zones suivies (Bafia pour le MVP)."""

    queryset = Zone.objects.filter(actif=True)
    serializer_class = ZoneSerializer
    lookup_field = "slug"


class PluieView(APIView):
    """Série journalière et début de saison des pluies."""

    @extend_schema(
        parameters=[
            OpenApiParameter("zone", str, description="Identifiant de zone (défaut : bafia)."),
            OpenApiParameter("debut", str, description="Début ISO (défaut : 365 jours avant la fin)."),
            OpenApiParameter("fin", str, description="Fin ISO (défaut : dernière donnée disponible)."),
        ],
        responses={200: dict},
    )
    def get(self, request):
        zone = zone_demandee(request)
        derniere = derniere_date(zone)
        if derniere is None:
            return Response(
                {
                    "zone": ZoneSerializer(zone).data,
                    "disponible": False,
                    "source": SOURCE_NASA,
                    "message": "Aucune donnée en base. Lancez : python manage.py ingest_power",
                }
            )

        fin = parse_date_param(request.query_params.get("fin"), "fin") or derniere
        debut = parse_date_param(request.query_params.get("debut"), "debut") or fin - timedelta(days=365)
        if debut > fin:
            raise ValidationError({"debut": "La date de début doit précéder la date de fin."})
        if (fin - debut).days > DUREE_MAX_SERIE_JOURS:
            raise ValidationError(
                {"fin": f"Période trop longue (maximum {DUREE_MAX_SERIE_JOURS} jours)."}
            )

        lignes = list(
            zone.weather.filter(date__range=(debut, fin))
            .order_by("date")
            .values("date", "precip_mm", "tmax_c", "tmin_c")
        )
        _, stats = saison(zone)

        return Response(
            {
                "zone": ZoneSerializer(zone).data,
                "disponible": bool(lignes),
                "source": SOURCE_NASA,
                "unite": {"precip_mm": "mm/jour", "tmax_c": "°C", "tmin_c": "°C"},
                "periode": {"debut": debut.isoformat(), "fin": fin.isoformat()},
                "derniere_donnee": derniere.isoformat(),
                "nb_jours": len(lignes),
                "serie": lignes,
                "resume_mensuel": analytics.monthly_summary(lignes),
                "debut_saison": {
                    "regle": season.REGLE,
                    "confiance": stats.get("confiance", "faible"),
                    "statistiques": stats,
                    "par_annee": stats.get("dates", []),
                },
            }
        )


class TendancesView(APIView):
    """Saison en cours comparée aux N années précédentes (Chart.js)."""

    @extend_schema(
        parameters=[
            OpenApiParameter("zone", str, description="Identifiant de zone (défaut : bafia)."),
            OpenApiParameter("annee", int, description="Année à comparer (défaut : dernière année de données)."),
            OpenApiParameter("annees_reference", int, description="Nombre d'années de référence (1 à 20, défaut 10)."),
        ],
        responses={200: dict},
    )
    def get(self, request):
        zone = zone_demandee(request)
        annee = request.query_params.get("annee")
        annee = parse_int_param(annee, "annee", 0, 1900, 2200) or None
        nb_reference = parse_int_param(
            request.query_params.get("annees_reference"), "annees_reference", 10, 1, 20
        )

        serie = list(zone.weather.order_by("date").values_list("date", "precip_mm", "tmax_c"))
        if not serie:
            return Response(
                {
                    "zone": ZoneSerializer(zone).data,
                    "disponible": False,
                    "source": SOURCE_NASA,
                    "message": "Aucune donnée en base. Lancez : python manage.py ingest_power",
                }
            )

        tendance = analytics.trend_comparison(serie, annee, nb_reference)
        return Response(
            {
                "zone": ZoneSerializer(zone).data,
                "disponible": True,
                "source": SOURCE_NASA,
                "unite": {"pluie": "mm/mois", "temperature": "°C"},
                "derniere_donnee": serie[-1][0].isoformat(),
                "tendance": tendance,
            }
        )


class RisquesView(APIView):
    """Risque de poche de sécheresse (Random Forest en phase 2, règle en phase 1)."""

    @extend_schema(
        parameters=[
            OpenApiParameter("zone", str, description="Identifiant de zone (défaut : bafia)."),
            OpenApiParameter("culture", str, description="Culture demandée (information)."),
        ],
        responses={200: dict},
    )
    def get(self, request):
        zone = zone_demandee(request)
        culture = (request.query_params.get("culture") or "maïs")[:50]
        resultat = evaluer_risque(zone)
        return Response(
            {
                "zone": ZoneSerializer(zone).data,
                "culture": culture,
                "culture_prise_en_compte": False,
                "note_culture": (
                    "La règle de la phase 1 est générique ; la sensibilité par culture "
                    "arrive avec le modèle de la phase 2."
                ),
                **resultat,
            }
        )


class CalendrierSemisView(APIView):
    """Fenêtre de semis recommandée, dérivée des débuts de saison observés."""

    @extend_schema(
        parameters=[
            OpenApiParameter("zone", str, description="Identifiant de zone (défaut : bafia)."),
            OpenApiParameter("annee", int, description="Année visée (défaut : année suivante)."),
        ],
        responses={200: dict},
    )
    def get(self, request):
        zone = zone_demandee(request)
        onsets, stats = saison(zone)
        derniere = derniere_date(zone)
        annee = request.query_params.get("annee")
        annee = parse_int_param(annee, "annee", 0, 1900, 2200) or (
            (derniere.year + 1) if derniere else date.today().year + 1
        )
        fenetre = season.fenetre_pour_annee(stats, annee)

        return Response(
            {
                "zone": ZoneSerializer(zone).data,
                "disponible": stats.get("disponible", False),
                "annee": annee,
                "fenetre_recommandee": fenetre,
                "confiance": stats.get("confiance", "faible"),
                "regle": season.REGLE,
                "historique": stats.get("dates", []),
                "statistiques": stats,
                "source": "règle de début de saison calculée sur NASA POWER",
                "a_valider_par_agronome": True,
                "note": (
                    "Fenêtre indicative de ±5 jours autour de la date médiane observée. "
                    "À confronter aux pratiques locales et à un agronome."
                ),
            }
        )


class PointView(APIView):
    """Valeurs locales pour un clic sur la carte (zone POWER la plus proche)."""

    @extend_schema(
        parameters=[
            OpenApiParameter("lat", float, required=True, description="Latitude WGS84."),
            OpenApiParameter("lon", float, required=True, description="Longitude WGS84."),
        ],
        responses={200: dict},
    )
    def get(self, request):
        latitude = parse_float_param(request.query_params.get("lat"), "lat", -90, 90)
        longitude = parse_float_param(request.query_params.get("lon"), "lon", -180, 180)

        zones = list(Zone.objects.filter(actif=True))
        if not zones:
            raise NotFound("Aucune zone active. Créez une zone dans l'administration.")

        zone = min(
            zones,
            key=lambda candidate: analytics.haversine_km(
                latitude, longitude, candidate.latitude, candidate.longitude
            ),
        )
        distance = analytics.haversine_km(
            latitude, longitude, zone.latitude, zone.longitude
        )

        recentes = list(
            zone.weather.order_by("-date")[:30].values_list("date", "precip_mm", "tmax_c")
        )
        recentes.reverse()
        resume = analytics.recent_summary(recentes)
        evaluation = evaluer_risque(zone)

        _, stats = saison(zone)
        annee = (recentes[-1][0].year + 1) if recentes else date.today().year + 1

        return Response(
            {
                "position": {"latitude": latitude, "longitude": longitude},
                "zone": ZoneSerializer(zone).data,
                "distance_km": round(distance, 1),
                "resolution": "grille NASA POWER ≈ 0,5° (zone la plus proche)",
                "disponible": resume.get("disponible", False),
                "source": SOURCE_NASA,
                "date_derniere_donnee": resume.get("derniere_date"),
                "meteo": resume,
                "risque": evaluation,
                "calendrier_semis": {
                    "annee": annee,
                    "fenetre_recommandee": season.fenetre_pour_annee(stats, annee),
                    "confiance": stats.get("confiance", "faible"),
                },
                "rotation": None,
                "rotation_note": "Le comparateur de rotations sera branché en phase 3.",
                "avertissement": (
                    "Valeurs issues de la maille POWER la plus proche, pas d'une parcelle. "
                    "À valider avec un agronome."
                ),
            }
        )
