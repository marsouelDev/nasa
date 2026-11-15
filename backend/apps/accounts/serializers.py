"""Sérialiseurs des comptes agriculteurs (phase 5)."""

from __future__ import annotations

from django.conf import settings
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers

from apps.data.models import Zone

from .consentement import TEXTE_CONSENTEMENT, VERSION_CONSENTEMENT
from .models import Agriculteur
from .telephones import masquer_telephone, normaliser_telephone


class AgriculteurPublicSerializer(serializers.ModelSerializer):
    """Vue publique d'un agriculteur : le numéro complet n'est jamais exposé."""

    telephone_masque = serializers.SerializerMethodField()
    zone = serializers.SlugRelatedField(slug_field="slug", read_only=True)
    zone_nom = serializers.CharField(source="zone.nom", read_only=True)
    peut_recevoir_sms = serializers.BooleanField(read_only=True)

    class Meta:
        model = Agriculteur
        fields = (
            "id",
            "telephone_masque",
            "nom",
            "zone",
            "zone_nom",
            "langue",
            "consentement",
            "consentement_le",
            "consentement_version",
            "desinscrit_le",
            "actif",
            "peut_recevoir_sms",
            "cree_le",
        )

    def get_telephone_masque(self, agriculteur: Agriculteur) -> str:
        return masquer_telephone(agriculteur.telephone)


class InscriptionSerializer(serializers.Serializer):
    """Données minimales d'inscription, avec consentement obligatoire."""

    telephone = serializers.CharField(max_length=30)
    zone = serializers.CharField(max_length=60, required=False, allow_blank=True, default="")
    langue = serializers.ChoiceField(
        choices=Agriculteur.Langue.choices, required=False, default=Agriculteur.Langue.FRANCAIS
    )
    nom = serializers.CharField(max_length=120, required=False, allow_blank=True, default="")
    consentement = serializers.BooleanField()

    def validate_telephone(self, valeur: str) -> str:
        try:
            return normaliser_telephone(valeur)
        except DjangoValidationError as erreur:
            raise serializers.ValidationError(erreur.messages) from erreur

    def validate_consentement(self, valeur: bool) -> bool:
        if not valeur:
            raise serializers.ValidationError(
                "Le consentement explicite est obligatoire pour recevoir des SMS. "
                f"Texte à accepter : « {TEXTE_CONSENTEMENT} »"
            )
        return valeur

    def validate_zone(self, valeur: str) -> Zone:
        slug = valeur or settings.DEFAULT_ZONE_SLUG
        zone = Zone.objects.filter(slug=slug, actif=True).first()
        if zone is None:
            raise serializers.ValidationError(f"Zone « {slug} » inconnue ou inactive.")
        return zone

    def create(self, validated_data: dict) -> tuple[Agriculteur, bool]:
        """Crée ou réactive l'inscription, puis enregistre le consentement daté."""
        telephone = validated_data["telephone"]
        agriculteur = Agriculteur.objects.filter(telephone=telephone).first()
        cree = agriculteur is None
        if agriculteur is None:
            agriculteur = Agriculteur(telephone=telephone)

        agriculteur.zone = validated_data["zone"]
        agriculteur.langue = validated_data["langue"]
        if validated_data.get("nom"):
            agriculteur.nom = validated_data["nom"]
        agriculteur.accorder_consentement(TEXTE_CONSENTEMENT, VERSION_CONSENTEMENT)
        agriculteur.save()
        return agriculteur, cree


class DesinscriptionSerializer(serializers.Serializer):
    telephone = serializers.CharField(max_length=30)

    def validate_telephone(self, valeur: str) -> str:
        try:
            return normaliser_telephone(valeur)
        except DjangoValidationError as erreur:
            raise serializers.ValidationError(erreur.messages) from erreur
