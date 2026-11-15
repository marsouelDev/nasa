"""Envoi SMS via Africa's Talking, avec simulation par défaut (phase 5).

Sécurité : aucun appel réseau n'est effectué tant que `SMS_SIMULATION` n'est
pas explicitement passée à False **et** que les clés et `SMS_ENVOI_REEL=True`
sont fournies. Un message n'est jamais préparé sans consentement enregistré.

Le mode réel est implémenté pour la mise en service, mais n'est pas utilisé
dans le MVP : la démonstration se contente de journaliser le SMS.
"""

from __future__ import annotations

import logging
from typing import Any

import requests
from django.conf import settings
from django.utils import timezone

from apps.accounts.models import Agriculteur
from apps.accounts.telephones import masquer_telephone

from .models import EnvoiSMS

logger = logging.getLogger(__name__)

LONGUEUR_MAX_SMS = 160
SOURCE_SMS = "Africa's Talking (mode simulé par défaut)"
TIMEOUT_SECONDES = 20


class ConsentementManquant(PermissionError):
    """Levée quand un envoi est demandé sans consentement valide."""


class MessageSMSInvalide(ValueError):
    """Levée quand le message est vide ou dépasse 160 caractères."""


def simulation_active() -> bool:
    """Vrai si aucun appel réel à Africa's Talking ne doit être fait."""
    if settings.SMS_SIMULATION:
        return True
    if not settings.AT_API_KEY or not settings.AT_USERNAME:
        return True
    return not settings.SMS_ENVOI_REEL


def _nom_court(nom: str) -> str:
    return (nom or "").strip()[:24]


def construire_sms_risque(nom_zone: str, risque: dict, langue: str = "fr") -> str:
    """Compose un SMS d'alerte de 160 caractères au plus.

    Le message porte toujours la confiance et la mention de validation par un
    agronome, comme toute recommandation AgroSentry.
    """
    zone = _nom_court(nom_zone)
    if not risque.get("disponible"):
        if langue == "en":
            return (
                f"AgroSentry {zone}: weather data unavailable. "
                "Validate with an agronomist. Reply STOP to opt out."
            )[:LONGUEUR_MAX_SMS]
        return (
            f"AgroSentry {zone} : données météo indisponibles. "
            "À valider avec un agronome. STOP pour quitter."
        )[:LONGUEUR_MAX_SMS]

    niveau = str(risque.get("niveau") or "inconnu").lower()
    confiance = str(risque.get("confiance") or "faible").lower()
    score = risque.get("score")
    score_txt = f", score {score:.2f}" if isinstance(score, (int, float)) else ""

    if langue == "en":
        niveaux = {"faible": "LOW", "moyen": "MEDIUM", "élevé": "HIGH"}
        message = (
            f"AgroSentry {zone}: drought risk {niveaux.get(niveau, niveau.upper())}"
            f"{score_txt}, confidence {confiance}. "
            "Validate with an agronomist. Reply STOP to opt out."
        )
    else:
        message = (
            f"AgroSentry {zone} : risque de sécheresse {niveau.upper()}"
            f"{score_txt}, confiance {confiance}. "
            "À valider avec un agronome. STOP pour quitter."
        )
    return message[:LONGUEUR_MAX_SMS]


def _envoyer_africa_talking(destinataire: str, message: str) -> tuple[str, str]:
    """Appelle la passerelle réelle ; retourne (référence, erreur).

    N'est atteint que si la simulation est explicitement désactivée.
    """
    donnees = {
        "username": settings.AT_USERNAME,
        "to": destinataire,
        "message": message,
    }
    if settings.AT_SENDER_ID:
        donnees["from"] = settings.AT_SENDER_ID

    reponse = requests.post(
        settings.AT_API_URL,
        headers={
            "apiKey": settings.AT_API_KEY,
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept": "application/json",
        },
        data=donnees,
        timeout=TIMEOUT_SECONDES,
    )
    reponse.raise_for_status()
    donnees: dict[str, Any] = reponse.json()
    destinataires = (donnees.get("SMSMessageData") or {}).get("Recipients") or []
    if not destinataires:
        return "", "Réponse Africa's Talking sans destinataire."
    premier = destinataires[0]
    if premier.get("statusCode") != 101:
        return (
            str(premier.get("messageId") or ""),
            f"Statut Africa's Talking : {premier.get('status') or premier.get('statusCode')}",
        )
    return str(premier.get("messageId") or ""), ""


def envoyer_sms(
    agriculteur: Agriculteur,
    message: str,
    *,
    categorie: str = EnvoiSMS.Categorie.TEST,
) -> EnvoiSMS:
    """Prépare (simulation) ou envoie un SMS à un agriculteur consenti.

    Lève `ConsentementManquant` avant toute écriture si l'agriculteur n'a pas
    de consentement valide, et `MessageSMSInvalide` si le texte est vide ou
    trop long.
    """
    if not agriculteur.peut_recevoir_sms:
        raise ConsentementManquant(
            "Aucun SMS ne peut être préparé : consentement absent, retiré ou "
            "agriculteur désinscrit."
        )

    texte = (message or "").strip()
    if not texte:
        raise MessageSMSInvalide("Le message SMS est vide.")
    if len(texte) > LONGUEUR_MAX_SMS:
        raise MessageSMSInvalide(
            f"Message de {len(texte)} caractères : la limite est {LONGUEUR_MAX_SMS}."
        )

    simulation = simulation_active()
    statut = EnvoiSMS.Statut.SIMULE
    mode = EnvoiSMS.Mode.SIMULATION
    reference = ""
    erreur = ""

    if not simulation:
        mode = EnvoiSMS.Mode.REEL
        try:
            reference, erreur = _envoyer_africa_talking(agriculteur.telephone, texte)
            statut = EnvoiSMS.Statut.ECHEC if erreur else EnvoiSMS.Statut.ENVOYE
        except requests.RequestException as probleme:
            logger.warning("Échec de l'envoi SMS vers %s : %s", agriculteur.telephone, probleme)
            statut = EnvoiSMS.Statut.ECHEC
            erreur = str(probleme)
        except (ValueError, KeyError) as probleme:
            logger.warning("Réponse Africa's Talking illisible : %s", probleme)
            statut = EnvoiSMS.Statut.ECHEC
            erreur = f"Réponse illisible : {probleme}"

    return EnvoiSMS.objects.create(
        agriculteur=agriculteur,
        destinataire=agriculteur.telephone,
        message=texte,
        longueur=len(texte),
        statut=statut,
        mode=mode,
        categorie=categorie,
        reference=reference,
        erreur=erreur,
    )


def resume_journal(limite: int = 20) -> dict:
    """Derniers envois, numéros masqués, pour la console de démonstration."""
    envois = EnvoiSMS.objects.all()[:limite]
    return {
        "simulation": simulation_active(),
        "longueur_max": LONGUEUR_MAX_SMS,
        "source": SOURCE_SMS,
        "genere_le": timezone.now().isoformat(),
        "envois": [
            {
                "id": envoi.id,
                "telephone_masque": masquer_telephone(envoi.destinataire),
                "message": envoi.message,
                "longueur": envoi.longueur,
                "statut": envoi.statut,
                "mode": envoi.mode,
                "categorie": envoi.categorie,
                "reference": envoi.reference,
                "cree_le": envoi.cree_le.isoformat(),
            }
            for envoi in envois
        ],
    }
