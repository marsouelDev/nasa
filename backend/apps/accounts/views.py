"""API des comptes agriculteurs et du consentement (phase 5).

Ces routes sont ouvertes en démonstration : aucun jeton n'est exigé pour
s'inscrire depuis la console. En production, elles devront être protégées
(jeton ou signature) avant toute collecte réelle.
"""

from __future__ import annotations

from django.core.exceptions import ValidationError as DjangoValidationError
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from .consentement import TEXTE_CONSENTEMENT, VERSION_CONSENTEMENT
from .models import Agriculteur
from .serializers import (
    AgriculteurPublicSerializer,
    DesinscriptionSerializer,
    InscriptionSerializer,
)
from .telephones import masquer_telephone, normaliser_telephone


class InscriptionView(APIView):
    """Inscription d'un agriculteur, avec consentement explicite obligatoire."""

    permission_classes = [AllowAny]

    @extend_schema(request=InscriptionSerializer, responses={201: dict, 200: dict})
    def post(self, request):
        entree = InscriptionSerializer(data=request.data)
        entree.is_valid(raise_exception=True)
        agriculteur, cree = entree.save()
        return Response(
            {
                "cree": cree,
                "consentement_enregistre": True,
                "version_consentement": agriculteur.consentement_version,
                "agriculteur": AgriculteurPublicSerializer(agriculteur).data,
                "message": (
                    "Inscription enregistrée. Les SMS restent simulés tant que la "
                    "passerelle n'est pas configurée."
                ),
            },
            status=status.HTTP_201_CREATED if cree else status.HTTP_200_OK,
        )

    @extend_schema(responses={200: dict})
    def get(self, request):
        """Résumé agrégé : aucun numéro, même masqué, dans cette vue."""
        return Response(
            {
                "nombre_agriculteurs": Agriculteur.objects.count(),
                "nombre_consentants": Agriculteur.objects.filter(
                    consentement=True,
                    consentement_le__isnull=False,
                    desinscrit_le__isnull=True,
                    actif=True,
                ).count(),
                "texte_consentement": TEXTE_CONSENTEMENT,
                "version_consentement": VERSION_CONSENTEMENT,
                "langues": [
                    {"code": code, "libelle": libelle}
                    for code, libelle in Agriculteur.Langue.choices
                ],
            }
        )


class StatutInscriptionView(APIView):
    """État d'un numéro (masqué) pour la console de démonstration."""

    permission_classes = [AllowAny]

    @extend_schema(responses={200: dict})
    def get(self, request):
        valeur = request.query_params.get("telephone", "")
        try:
            telephone = normaliser_telephone(valeur)
        except DjangoValidationError:
            return Response(
                {"detail": "Numéro de téléphone invalide."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        agriculteur = Agriculteur.objects.filter(telephone=telephone).first()
        if agriculteur is None:
            return Response(
                {
                    "connu": False,
                    "telephone_masque": masquer_telephone(telephone),
                    "message": "Aucune inscription pour ce numéro.",
                }
            )
        return Response(
            {
                "connu": True,
                "agriculteur": AgriculteurPublicSerializer(agriculteur).data,
            }
        )


class DesinscriptionView(APIView):
    """Désinscription STOP : retire le consentement et bloque tout envoi."""

    permission_classes = [AllowAny]

    @extend_schema(request=DesinscriptionSerializer, responses={200: dict})
    def post(self, request):
        entree = DesinscriptionSerializer(data=request.data)
        entree.is_valid(raise_exception=True)
        telephone = entree.validated_data["telephone"]
        agriculteur = Agriculteur.objects.filter(telephone=telephone).first()

        if agriculteur is None:
            return Response(
                {
                    "connu": False,
                    "desinscrit": False,
                    "telephone_masque": masquer_telephone(telephone),
                    "message": "Aucune inscription pour ce numéro : rien à désinscrire.",
                }
            )

        deja_desinscrit = agriculteur.desinscrit_le is not None
        if not deja_desinscrit:
            agriculteur.retirer_consentement()
            agriculteur.save(update_fields=["consentement", "desinscrit_le", "maj_le"])

        return Response(
            {
                "connu": True,
                "desinscrit": True,
                "deja_desinscrit": deja_desinscrit,
                "telephone_masque": masquer_telephone(agriculteur.telephone),
                "desinscrit_le": agriculteur.desinscrit_le,
                "consentement": agriculteur.consentement,
                "message": "STOP enregistré : plus aucun SMS ne sera préparé pour ce numéro.",
            }
        )
