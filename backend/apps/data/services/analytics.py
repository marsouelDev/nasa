"""Agrégations lisibles pour l'API et les graphiques du frontend."""

from __future__ import annotations

import math
from collections import defaultdict
from datetime import date
from statistics import mean
from typing import Iterable

MOIS_FR = [
    "janvier",
    "février",
    "mars",
    "avril",
    "mai",
    "juin",
    "juillet",
    "août",
    "septembre",
    "octobre",
    "novembre",
    "décembre",
]


def monthly_summary(lignes: Iterable[dict]) -> list[dict]:
    """Cumuls de pluie et températures moyennes par mois."""
    pluies: dict[tuple[int, int], list[float]] = defaultdict(list)
    temperatures: dict[tuple[int, int], list[float]] = defaultdict(list)
    jours: dict[tuple[int, int], set[date]] = defaultdict(set)
    for ligne in lignes:
        cle = (ligne["date"].year, ligne["date"].month)
        jours[cle].add(ligne["date"])
        if ligne.get("precip_mm") is not None:
            pluies[cle].append(ligne["precip_mm"])
        if ligne.get("tmax_c") is not None:
            temperatures[cle].append(ligne["tmax_c"])

    resultat = []
    for annee, mois in sorted(set(pluies) | set(temperatures)):
        cle = (annee, mois)
        temp = temperatures.get(cle, [])
        resultat.append(
            {
                "mois": f"{annee:04d}-{mois:02d}",
                "libelle": f"{MOIS_FR[mois - 1]} {annee}",
                "pluie_mm": round(sum(pluies[cle]), 1) if pluies.get(cle) else None,
                "temp_moyenne_c": round(mean(temp), 1) if temp else None,
                "jours": len(jours[cle]),
            }
        )
    return resultat


def trend_comparison(
    serie: Iterable[tuple[date, float | None, float | None]],
    annee_courante: int | None = None,
    annees_reference: int = 10,
) -> dict:
    """Compare les mois d'une année aux N années précédentes."""
    pluie_mensuelle: dict[tuple[int, int], float] = defaultdict(float)
    pluie_presente: set[tuple[int, int]] = set()
    temp_mensuelle: dict[tuple[int, int], list[float]] = defaultdict(list)

    annees: set[int] = set()
    for jour, pluie, tmax in serie:
        annees.add(jour.year)
        cle = (jour.year, jour.month)
        if pluie is not None:
            pluie_mensuelle[cle] += pluie
            pluie_presente.add(cle)
        if tmax is not None:
            temp_mensuelle[cle].append(tmax)

    if annee_courante is None:
        annee_courante = max(annees) if annees else date.today().year
    annees_precedentes = sorted(annee for annee in annees if annee < annee_courante)
    reference = annees_precedentes[-annees_reference:] if annees_reference > 0 else []

    pluies_courantes: list[float | None] = []
    pluies_reference: list[float | None] = []
    temperatures_courantes: list[float | None] = []
    temperatures_reference: list[float | None] = []

    for mois in range(1, 13):
        cle = (annee_courante, mois)
        pluies_courantes.append(
            round(pluie_mensuelle[cle], 1) if cle in pluie_presente else None
        )
        temperatures_courantes.append(
            round(mean(temp_mensuelle[cle]), 1) if temp_mensuelle.get(cle) else None
        )

        pluies_annees = [
            pluie_mensuelle[(annee, mois)]
            for annee in reference
            if (annee, mois) in pluie_presente
        ]
        temperatures_annees = [
            mean(temp_mensuelle[(annee, mois)])
            for annee in reference
            if temp_mensuelle.get((annee, mois))
        ]
        pluies_reference.append(round(mean(pluies_annees), 1) if pluies_annees else None)
        temperatures_reference.append(
            round(mean(temperatures_annees), 1) if temperatures_annees else None
        )

    return {
        "annee_courante": annee_courante,
        "annees_reference": reference,
        "labels": [MOIS_FR[mois - 1] for mois in range(1, 13)],
        "pluie_courante_mm": pluies_courantes,
        "pluie_moyenne_reference_mm": pluies_reference,
        "temp_courante_c": temperatures_courantes,
        "temp_moyenne_reference_c": temperatures_reference,
    }


def recent_summary(serie: Iterable[tuple[date, float | None, float | None]], jours: int = 30) -> dict:
    """Résumé des derniers jours (pluie cumulée, températures)."""
    lignes = list(serie)
    if not lignes:
        return {
            "disponible": False,
            "message": "Aucune donnée météo en base pour cette zone.",
        }

    recentes = lignes[-jours:]
    pluies = [pluie for _, pluie, _ in recentes if pluie is not None]
    pluies_7j = [pluie for _, pluie, _ in lignes[-7:] if pluie is not None]
    temperatures = [tmax for _, _, tmax in recentes if tmax is not None]

    return {
        "disponible": True,
        "derniere_date": lignes[-1][0].isoformat(),
        "jours_couverts": len(recentes),
        "pluie_7j_mm": round(sum(pluies_7j), 1) if pluies_7j else None,
        "pluie_30j_mm": round(sum(pluies), 1) if pluies else None,
        "temp_max_moyenne_30j_c": round(mean(temperatures), 1) if temperatures else None,
    }


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Distance orthodromique en kilomètres."""
    rayon = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return 2 * rayon * math.asin(math.sqrt(a))
