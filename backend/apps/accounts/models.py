"""Comptes minimalistes des agriculteurs et consentement (phase 5).

Collecte volontairement limitée : numéro de téléphone, zone, langue et
consentement daté. Aucun mot de passe n'est demandé pour le MVP SMS/USSD.
"""

from __future__ import annotations

from django.db import models
from django.utils import timezone

from apps.data.models import Zone


class Agriculteur(models.Model):
    """Un destinataire de SMS, avec la preuve de son consentement.

    Aucun envoi ne doit avoir lieu si `peut_recevoir_sms` est faux.
    """

    class Langue(models.TextChoices):
        FRANCAIS = "fr", "Français"
        ANGLAIS = "en", "English"

    telephone = models.CharField(
        "téléphone",
        max_length=20,
        unique=True,
        help_text="Format normalisé +237XXXXXXXXX.",
    )
    nom = models.CharField("nom", max_length=120, blank=True)
    zone = models.ForeignKey(
        Zone, on_delete=models.PROTECT, related_name="agriculteurs", verbose_name="zone"
    )
    langue = models.CharField(
        "langue", max_length=5, choices=Langue.choices, default=Langue.FRANCAIS
    )

    consentement = models.BooleanField("consentement", default=False)
    consentement_le = models.DateTimeField("consentement donné le", null=True, blank=True)
    consentement_version = models.CharField("version du consentement", max_length=20, blank=True)
    consentement_texte = models.TextField("texte du consentement accepté", blank=True)
    desinscrit_le = models.DateTimeField("désinscrit le", null=True, blank=True)

    actif = models.BooleanField("actif", default=True)
    cree_le = models.DateTimeField("créé le", auto_now_add=True)
    maj_le = models.DateTimeField("modifié le", auto_now=True)

    class Meta:
        verbose_name = "agriculteur"
        verbose_name_plural = "agriculteurs"
        ordering = ["telephone"]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(consentement=False)
                | models.Q(consentement_le__isnull=False),
                name="consentement_date_obligatoire",
                violation_error_message=(
                    "Un consentement enregistré doit porter une date."
                ),
            ),
        ]

    def __str__(self) -> str:
        return self.telephone

    @property
    def peut_recevoir_sms(self) -> bool:
        """Vrai uniquement si actif, consenti et non désinscrit."""
        return bool(
            self.actif
            and self.consentement
            and self.consentement_le is not None
            and self.desinscrit_le is None
        )

    def accorder_consentement(self, texte: str, version: str) -> None:
        """Enregistre un consentement explicite, daté et versionné.

        Un agriculteur réinscrit après un STOP retrouve la possibilité de
        recevoir des SMS.
        """
        self.consentement = True
        self.consentement_le = timezone.now()
        self.consentement_texte = texte
        self.consentement_version = version
        self.desinscrit_le = None
        self.actif = True

    def retirer_consentement(self) -> None:
        """Applique un STOP : plus aucun SMS ne sera préparé pour ce numéro."""
        self.consentement = False
        self.desinscrit_le = timezone.now()
