"""Client de l'API NASA POWER (daily point).

Le cache est géré par la commande d'ingestion : ce module ne fait que
télécharger et normaliser une période demandée.
"""

from __future__ import annotations

import logging
import time
from datetime import date, timedelta
from typing import Iterable

import requests
from django.conf import settings

logger = logging.getLogger(__name__)

PARAMETRES = ("PRECTOTCORR", "T2M_MAX", "T2M_MIN")
COLONNES = {
    "PRECTOTCORR": "precip_mm",
    "T2M_MAX": "tmax_c",
    "T2M_MIN": "tmin_c",
}
COMMUNAUTE = "AG"


class PowerError(RuntimeError):
    """Erreur de communication ou de format avec l'API NASA POWER."""


def _nombre(valeur) -> float | None:
    """Convertit une valeur POWER en float, en traitant -999 comme absente."""
    try:
        nombre = float(valeur)
    except (TypeError, ValueError):
        return None
    if nombre <= -900:  # sentinelle POWER : -999
        return None
    return nombre


def parse_payload(payload: dict) -> dict[date, dict[str, float | None]]:
    """Transforme la réponse POWER en {date: {precip_mm, tmax_c, tmin_c}}."""
    try:
        parametres = payload["properties"]["parameter"]
    except (KeyError, TypeError) as exc:
        raise PowerError("Réponse NASA POWER inattendue : bloc 'properties.parameter' absent.") from exc

    manquants = [nom for nom in PARAMETRES if nom not in parametres]
    if manquants:
        raise PowerError(f"Paramètres absents de la réponse POWER : {', '.join(manquants)}")

    cles = sorted(set().union(*(parametres[nom].keys() for nom in PARAMETRES)))
    resultat: dict[date, dict[str, float | None]] = {}
    for cle in cles:
        try:
            jour = date(int(cle[0:4]), int(cle[4:6]), int(cle[6:8]))
        except (TypeError, ValueError) as exc:
            raise PowerError(f"Date invalide renvoyée par POWER : {cle!r}") from exc
        resultat[jour] = {COLONNES[nom]: _nombre(parametres[nom][cle]) for nom in PARAMETRES}
    return resultat


def fetch_interval(
    zone,
    debut: date,
    fin: date,
    *,
    session=None,
    timeout: int | None = None,
    max_retries: int | None = None,
    sleep=time.sleep,
) -> dict[date, dict[str, float | None]]:
    """Télécharge [debut, fin] pour une zone, avec nouvelles tentatives."""
    if debut > fin:
        raise ValueError("La date de début doit précéder la date de fin.")

    timeout = settings.POWER_TIMEOUT if timeout is None else timeout
    max_retries = settings.POWER_MAX_RETRIES if max_retries is None else max_retries
    parametres = {
        "parameters": ",".join(PARAMETRES),
        "community": COMMUNAUTE,
        "latitude": f"{zone.latitude:.4f}",
        "longitude": f"{zone.longitude:.4f}",
        "start": debut.strftime("%Y%m%d"),
        "end": fin.strftime("%Y%m%d"),
        "format": "JSON",
    }

    derniere_erreur: Exception | None = None
    for tentative in range(1, max_retries + 1):
        try:
            client = session if session is not None else requests
            reponse = client.get(settings.POWER_API_URL, params=parametres, timeout=timeout)
            reponse.raise_for_status()
            return parse_payload(reponse.json())
        except PowerError as exc:
            derniere_erreur = exc
        except (requests.RequestException, ValueError) as exc:
            derniere_erreur = exc

        logger.warning(
            "NASA POWER : tentative %s/%s échouée (%s)", tentative, max_retries, derniere_erreur
        )
        if tentative < max_retries:
            sleep(2 ** (tentative - 1))

    raise PowerError(
        f"NASA POWER injoignable après {max_retries} tentatives : {derniere_erreur}"
    )


def decouper_periode(debut: date, fin: date, jours_par_lot: int = 366 * 5) -> list[tuple[date, date]]:
    """Découpe une période en lots pour limiter la taille des requêtes."""
    lots: list[tuple[date, date]] = []
    curseur = debut
    while curseur <= fin:
        fin_lot = min(curseur + timedelta(days=jours_par_lot - 1), fin)
        lots.append((curseur, fin_lot))
        curseur = fin_lot + timedelta(days=1)
    return lots


def periodes_manquantes(
    debut: date, fin: date, dates_existantes: Iterable[date]
) -> list[tuple[date, date]]:
    """Renvoie les intervalles contigus de dates absentes de la base."""
    existantes = set(dates_existantes)
    manquantes: list[tuple[date, date]] = []
    curseur = debut
    while curseur <= fin:
        if curseur in existantes:
            curseur += timedelta(days=1)
            continue
        debut_trou = curseur
        while curseur <= fin and curseur not in existantes:
            curseur += timedelta(days=1)
        manquantes.append((debut_trou, curseur - timedelta(days=1)))
    return manquantes
