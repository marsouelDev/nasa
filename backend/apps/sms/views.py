"""API du simulateur SMS et du journal (phase 5).

Comme les comptes, ces routes sont ouvertes pour la démonstration locale.
Elles n'envoient aucun message réel sans configuration explicite.
"""

from __future__ import annotations

from django.core.exceptions import ValidationError as DjangoValidationError
from drf_spectacular.utils import extend_schema
from rest_framework import serializers, status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.models import Agriculteur
from apps.accounts.telephones import masquer_telephone, normaliser_telephone
from apps.data.utils import parse_int_param
from apps.data.views import evaluer_risque, zone_demandee

from .models import EnvoiSMS
from .services import (
    LONGUEUR_MAX_SMS,
    SOURCE_SMS,
    ConsentementManquant,
    MessageSMSInvalide,
    construire_sms_risque,
    envoyer_sms,
    resume_journal,
    simulation_active,
)


class SimulationSMSSerializer(serializers.Serializer):
    telephone = serializers.CharField(max_length=30)
    message = serializers.CharField(required=False, allow_blank=True, default="")

    def validate_telephone(self, valeur: str) -> str:
        try:
            return normaliser_telephone(valeur)
        except DjangoValidationError as erreur:
            raise serializers.ValidationError(erreur.messages) from erreur


def _etat_consentement(agriculteur: Agriculteur) -> str:
    if agriculteur.desinscrit_le is not None:
        return "désinscrit (STOP)"
    if not agriculteur.consentement or agriculteur.consentement_le is None:
        return "sans consentement"
    if not agriculteur.actif:
        return "inactif"
    return "consentant"


class ApercuSMSView(APIView):
    """Aperçu du SMS de risque, sans destinataire ni envoi."""

    permission_classes = [AllowAny]

    @extend_schema(responses={200: dict})
    def get(self, request):
        zone = zone_demandee(request)
        langue = (request.query_params.get("langue") or "fr")[:5]
        risque = evaluer_risque(zone)
        message = construire_sms_risque(zone.nom, risque, langue=langue)
        return Response(
            {
                "zone": {"slug": zone.slug, "nom": zone.nom},
                "langue": langue,
                "disponible": risque.get("disponible", False),
                "risque": {
                    "niveau": risque.get("niveau"),
                    "score": risque.get("score"),
                    "confiance": risque.get("confiance"),
                    "source": risque.get("source"),
                },
                "message": message,
                "longueur": len(message),
                "longueur_max": LONGUEUR_MAX_SMS,
                "source_sms": SOURCE_SMS,
                "simulation": simulation_active(),
                "a_valider_par_agronome": True,
            }
        )


class SimulerSMSView(APIView):
    """Prépare un SMS pour un agriculteur inscrit et consentant.

    Sans consentement enregistré, la requête est refusée : aucun SMS n'est
    journalisé ni transmis.
    """

    permission_classes = [AllowAny]

    @extend_schema(request=SimulationSMSSerializer, responses={201: dict})
    def post(self, request):
        entree = SimulationSMSSerializer(data=request.data)
        entree.is_valid(raise_exception=True)
        telephone = entree.validated_data["telephone"]
        agriculteur = Agriculteur.objects.filter(telephone=telephone).first()

        if agriculteur is None:
            return Response(
                {
                    "detail": (
                        "Aucune inscription pour ce numéro. Enregistrez d'abord un "
                        "consentement explicite via /api/inscriptions/."
                    ),
                    "consentement_requis": True,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        if not agriculteur.peut_recevoir_sms:
            return Response(
                {
                    "detail": (
                        "Aucun SMS préparé : consentement absent, retiré ou "
                        "agriculteur désinscrit."
                    ),
                    "consentement_requis": True,
                    "etat": _etat_consentement(agriculteur),
                    "telephone_masque": masquer_telephone(agriculteur.telephone),
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        message = (entree.validated_data.get("message") or "").strip()
        if not message:
            risque = evaluer_risque(agriculteur.zone)
            if not risque.get("disponible"):
                return Response(
                    {
                        "detail": "Risque indisponible pour cette zone : message impossible à construire.",
                        "risque": risque,
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )
            message = construire_sms_risque(
                agriculteur.zone.nom, risque, langue=agriculteur.langue
            )

        try:
            envoi = envoyer_sms(agriculteur, message, categorie=EnvoiSMS.Categorie.TEST)
        except MessageSMSInvalide as probleme:
            return Response(
                {"detail": str(probleme), "longueur_max": LONGUEUR_MAX_SMS},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except ConsentementManquant as probleme:
            return Response(
                {"detail": str(probleme), "consentement_requis": True},
                status=status.HTTP_403_FORBIDDEN,
            )

        return Response(
            {
                "envoye": True,
                "simulation": envoi.mode == EnvoiSMS.Mode.SIMULATION,
                "longueur_max": LONGUEUR_MAX_SMS,
                "sms": {
                    "id": envoi.id,
                    "telephone_masque": masquer_telephone(envoi.destinataire),
                    "message": envoi.message,
                    "longueur": envoi.longueur,
                    "statut": envoi.statut,
                    "mode": envoi.mode,
                    "categorie": envoi.categorie,
                    "cree_le": envoi.cree_le,
                },
                "message_utilisateur": (
                    "SMS simulé : rien n'a été transmis."
                    if envoi.mode == EnvoiSMS.Mode.SIMULATION
                    else "SMS transmis à la passerelle."
                ),
            },
            status=status.HTTP_201_CREATED,
        )


class JournalSMSView(APIView):
    """Journal des envois, numéros masqués."""

    permission_classes = [AllowAny]

    @extend_schema(responses={200: dict})
    def get(self, request):
        limite = parse_int_param(request.query_params.get("limite"), "limite", 20, 1, 100)
        return Response(resume_journal(limite))
