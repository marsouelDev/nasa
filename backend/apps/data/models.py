"""Modèles de données AgroSentry : zones et séries météo NASA POWER."""

from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models


class Zone(models.Model):
    """Zone pilote (Bafia pour le MVP). Les coordonnées sont en base, pas en dur."""

    nom = models.CharField("nom", max_length=120)
    slug = models.SlugField("identifiant", max_length=60, unique=True)
    pays = models.CharField("pays", max_length=80, default="Cameroun")
    latitude = models.FloatField(
        "latitude",
        validators=[MinValueValidator(-90), MaxValueValidator(90)],
        help_text="Latitude décimale WGS84.",
    )
    longitude = models.FloatField(
        "longitude",
        validators=[MinValueValidator(-180), MaxValueValidator(180)],
        help_text="Longitude décimale WGS84.",
    )
    altitude_m = models.FloatField("altitude (m)", null=True, blank=True)
    actif = models.BooleanField("active", default=True)
    cree_le = models.DateTimeField("créée le", auto_now_add=True)

    class Meta:
        verbose_name = "zone"
        verbose_name_plural = "zones"
        ordering = ["nom"]

    def __str__(self) -> str:
        return f"{self.nom} ({self.latitude:.2f}, {self.longitude:.2f})"


class DailyWeather(models.Model):
    """Une journée de données météo pour une zone.

    Les valeurs absentes restent NULL : NASA POWER renvoie -999 pour un jour
    sans donnée, valeur convertie à l'ingestion et jamais stockée telle quelle.
    """

    zone = models.ForeignKey(Zone, on_delete=models.CASCADE, related_name="weather")
    date = models.DateField("date")
    precip_mm = models.FloatField("précipitations (mm)", null=True, blank=True)
    tmax_c = models.FloatField("température max (°C)", null=True, blank=True)
    tmin_c = models.FloatField("température min (°C)", null=True, blank=True)
    source = models.CharField("source", max_length=64, default="NASA POWER")
    ingere_le = models.DateTimeField("ingéré le", auto_now=True)

    class Meta:
        verbose_name = "donnée météo journalière"
        verbose_name_plural = "données météo journalières"
        ordering = ["-date"]
        constraints = [
            models.UniqueConstraint(fields=["zone", "date"], name="unique_zone_date"),
        ]
        indexes = [
            models.Index(fields=["zone", "-date"], name="idx_weather_zone_date"),
        ]

    def __str__(self) -> str:
        return f"{self.zone.slug} {self.date}"


class IngestionLog(models.Model):
    """Trace d'une exécution de `ingest_power` (audit et diagnostic)."""

    class Statut(models.TextChoices):
        SUCCES = "succes", "Succès"
        PARTIEL = "partiel", "Partiel"
        ERREUR = "erreur", "Erreur"

    zone = models.ForeignKey(
        Zone, on_delete=models.SET_NULL, null=True, blank=True, related_name="ingestions"
    )
    debut = models.DateField("début demandé")
    fin = models.DateField("fin demandée")
    statut = models.CharField("statut", max_length=16, choices=Statut.choices)
    jours_recus = models.PositiveIntegerField("jours reçus", default=0)
    jours_ignores = models.PositiveIntegerField("jours ignorés", default=0)
    message = models.TextField("message", blank=True)
    cree_le = models.DateTimeField("créé le", auto_now_add=True)
    termine_le = models.DateTimeField("terminé le", null=True, blank=True)

    class Meta:
        verbose_name = "journal d'ingestion"
        verbose_name_plural = "journaux d'ingestion"
        ordering = ["-cree_le"]

    def __str__(self) -> str:
        return f"{self.zone} {self.debut}→{self.fin} ({self.statut})"
