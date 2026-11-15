"""Début de la saison des pluies : règle explicable, sans modèle opaque.

Règle : premier jour entre le 1er mars et le 30 juin dont le cumul de pluie
sur les 10 jours précédents (jour inclus) atteint au moins 40 mm.
"""

from __future__ import annotations

import statistics
from datetime import date, timedelta
from typing import Iterable

FENETRE_JOURS = 10
SEUIL_MM = 40.0
MOIS_DEBUT = 3
MOIS_FIN = 6
FENETRE_SEMIS_JOURS = 5

REGLE = (
    "Premier jour entre le 1er mars et le 30 juin dont le cumul de pluie des "
    "10 jours précédents (jour inclus) atteint 40 mm."
)


def onset_dates(serie: Iterable[tuple[date, float | None]]) -> dict[int, date]:
    """Renvoie {année: date de début de saison} pour une série journalière."""
    valeurs: dict[date, float | None] = {jour: pluie for jour, pluie in serie}
    resultat: dict[int, date] = {}

    for annee in sorted({jour.year for jour in valeurs}):
        bornes = (date(annee, MOIS_DEBUT, 1), date(annee, MOIS_FIN, 30))
        for jour in sorted(j for j in valeurs if j.year == annee):
            if not (bornes[0] <= jour <= bornes[1]):
                continue
            fenetre = [
                valeurs.get(jour - timedelta(days=decalage))
                for decalage in range(FENETRE_JOURS - 1, -1, -1)
            ]
            if any(valeur is None for valeur in fenetre):
                continue
            if sum(fenetre) >= SEUIL_MM:
                resultat[annee] = jour
                break
    return resultat


def _date_depuis_jour_annee(jour_annee: int) -> date:
    """Convertit un jour de l'année (base 2001, année non bissextile) en date."""
    return date(2001, 1, 1) + timedelta(days=jour_annee - 1)


def _jour_annee(jour: date) -> int:
    return (jour - date(jour.year, 1, 1)).days + 1


def onset_statistics(onsets: dict[int, date]) -> dict:
    """Statistiques simples et niveau de confiance sur les dates observées."""
    if not onsets:
        return {
            "disponible": False,
            "annees": 0,
            "regle": REGLE,
            "confiance": "faible",
            "message": "Aucun début de saison détecté dans les données disponibles.",
        }

    jours = [_jour_annee(jour) for jour in onsets.values()]
    median = int(round(statistics.median(jours)))
    ecart = round(statistics.pstdev(jours), 1) if len(jours) > 1 else 0.0
    mediane = _date_depuis_jour_annee(median)

    if len(jours) >= 8 and ecart <= 10:
        confiance = "élevée"
    elif len(jours) >= 4 and ecart <= 18:
        confiance = "moyenne"
    else:
        confiance = "faible"

    return {
        "disponible": True,
        "annees": len(jours),
        "mediane": mediane.strftime("%m-%d"),
        "ecart_type_jours": ecart,
        "regle": REGLE,
        "confiance": confiance,
        "dates": [
            {"annee": annee, "date": jour.isoformat()} for annee, jour in sorted(onsets.items())
        ],
    }


def fenetre_pour_annee(stats: dict, annee: int) -> dict | None:
    """Convertit la médiane climatologique en fenêtre de semis pour une année."""
    if not stats.get("disponible"):
        return None
    # La médiane est fournie au format MM-DD ; on la reconstitue pour l'année visée.
    try:
        mois, jour = (int(partie) for partie in stats["mediane"].split("-"))
    except (KeyError, ValueError):
        return None
    milieu = date(annee, mois, jour)
    return {
        "debut": (milieu - timedelta(days=FENETRE_SEMIS_JOURS)).isoformat(),
        "fin": (milieu + timedelta(days=FENETRE_SEMIS_JOURS)).isoformat(),
    }
