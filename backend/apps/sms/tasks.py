"""Tâches Celery AgroSentry (phase 5)."""

from __future__ import annotations

from celery import shared_task

from apps.accounts.models import Agriculteur
from apps.accounts.telephones import masquer_telephone
from apps.data.models import Zone
from apps.data.views import evaluer_risque
from apps.sms.models import EnvoiSMS
from apps.sms.services import construire_sms_risque, envoyer_sms


@shared_task(
    name="sms.envoyer_alertes_risque",
    bind=True,
    max_retries=0,
)
def envoyer_alertes_risque(self, zone_slug: str | None = None) -> dict:
    """Évalue les risques et prépare les alertes SMS des consentants.

    En mode eager, la tâche s'exécute immédiatement à l'appel (endpoint
    `/api/sms/alertes/` ou command `envoyer_alertes`). Seuls les
    agriculteurs consentants sont destinataires ; la non-consentance bloque
    tout envoi et toute journalisation.
    """
    zones = list(Zone.objects.filter(actif=True).order_by("pk"))
    if zone_slug:
        zones = [zone for zone in zones if zone.slug == zone_slug]
    if not zones:
        return {"zones": [], "alertes": 0, "envoies_crees": 0, "ignores": []}

    resume = {
        "zones": [],
        "alertes": 0,
        "envoies_crees": 0,
        "ignores": [],
    }

    for zone in zones:
        risque = evaluer_risque(zone)
        if not risque.get("disponible"):
            resume["zones"].append({"zone": zone.slug, "alerte": False})
            continue

        agriculteurs = [
            agriculteur
            for agriculteur in Agriculteur.objects.filter(zone=zone).order_by("pk")
            if agriculteur.peut_recevoir_sms
        ]
        alertes = 0
        envoies_crees = 0
        ignores: list[dict] = []

        for agriculteur in agriculteurs:
            message = construire_sms_risque(zone.nom, risque, langue=agriculteur.langue)
            try:
                envoi = envoyer_sms(
                    agriculteur, message, categorie=EnvoiSMS.Categorie.ALERTE_RISQUE
                )
            except Exception:
                ignores.append(
                    {
                        "telephone_masque": masquer_telephone(agriculteur.telephone),
                        "raison": "consentement_requis",
                    }
                )
                continue
            alertes += 1
            envoies_crees += 1

        resume["zones"].append(
            {
                "zone": zone.slug,
                "alerte": bool(alertes),
                "niveau": risque.get("niveau"),
                "nb_consentants": len(agriculteurs),
                "alertes_envoyees": alertes,
            }
        )
        resume["alertes"] += alertes
        resume["envoies_crees"] += envoies_crees
        if ignores:
            resume["ignores"].extend(ignores)

    return resume
