"""Journal des SMS préparés ou envoyés (phase 5).

Même en simulation, chaque message est tracé : destinataire, texte exact,
longueur, statut et mode d'envoi. C'est la preuve que rien n'est parti quand
la passerelle n'est pas configurée.
"""

from __future__ import annotations

from django.db import models

from apps.accounts.models import Agriculteur


class EnvoiSMS(models.Model):
    class Statut(models.TextChoices):
        SIMULE = "simule", "Simulé (non transmis)"
        ENVOYE = "envoye", "Envoyé"
        ECHEC = "echec", "Échec"

    class Mode(models.TextChoices):
        SIMULATION = "simulation", "Simulation"
        REEL = "reel", "Passerelle réelle"

    class Categorie(models.TextChoices):
        ALERTE_RISQUE = "alerte_risque", "Alerte de risque"
        TEST = "test", "Message de test"
        USSD = "ussd", "Réponse USSD"
        AUTRE = "autre", "Autre"

    agriculteur = models.ForeignKey(
        Agriculteur,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="sms",
        verbose_name="agriculteur",
    )
    destinataire = models.CharField(
        "destinataire", max_length=20, help_text="Numéro normalisé au moment de l'envoi."
    )
    message = models.TextField("message")
    longueur = models.PositiveIntegerField("longueur (caractères)")
    statut = models.CharField("statut", max_length=12, choices=Statut.choices)
    mode = models.CharField("mode", max_length=12, choices=Mode.choices)
    categorie = models.CharField(
        "catégorie", max_length=20, choices=Categorie.choices, default=Categorie.AUTRE
    )
    reference = models.CharField(
        "référence opérateur", max_length=120, blank=True, help_text="Identifiant du message chez le fournisseur."
    )
    erreur = models.TextField("erreur", blank=True)
    cree_le = models.DateTimeField("créé le", auto_now_add=True)

    class Meta:
        verbose_name = "envoi SMS"
        verbose_name_plural = "envois SMS"
        ordering = ["-cree_le"]
        indexes = [models.Index(fields=["-cree_le"], name="idx_sms_cree_le")]

    def __str__(self) -> str:
        return f"{self.destinataire} ({self.statut}, {self.longueur} car.)"
