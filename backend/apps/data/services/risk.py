"""Risque de poche de sécheresse : règle simple et explicable (phase 1).

La phase 2 remplacera cette règle par le Random Forest entraîné sur les
données NASA POWER. En attendant, chaque réponse est étiquetée comme règle.
"""

from __future__ import annotations

from datetime import date
from typing import Iterable

SEUIL_PLUIE_SECHE_MM = 1.0
SEUIL_JOURS_SECS_ELEVE = 10
SEUIL_JOURS_SECS_MOYEN = 6
FENETRE_ANALYSE_JOURS = 30

SOURCE = "règle simple de poche de sécheresse (phase 1)"


def jours_secs_consecutifs(
    serie: Iterable[tuple[date, float | None]], seuil_mm: float = SEUIL_PLUIE_SECHE_MM
) -> int:
    """Nombre de jours consécutifs sans pluie en fin de série.

    Une valeur manquante interrompt le décompte : on ne suppose pas un jour sec.
    """
    total = 0
    for _, pluie in reversed(list(serie)):
        if pluie is None or pluie >= seuil_mm:
            break
        total += 1
    return total


def assess(
    serie: Iterable[tuple[date, float | None]], fenetre_jours: int = FENETRE_ANALYSE_JOURS
) -> dict:
    """Évalue le risque à partir des jours les plus récents."""
    lignes = list(serie)
    if not lignes:
        return {
            "disponible": False,
            "niveau": None,
            "confiance": "faible",
            "source": SOURCE,
            "message": "Aucune donnée météo en base pour cette zone.",
            "a_valider_par_agronome": True,
        }

    recentes = lignes[-fenetre_jours:]
    jours_secs = jours_secs_consecutifs(recentes)
    pluies = [pluie for _, pluie in recentes if pluie is not None]
    valeurs_manquantes = sum(1 for _, pluie in recentes if pluie is None)
    pluie_cumulee = round(sum(pluies), 1) if pluies else None

    if jours_secs >= SEUIL_JOURS_SECS_ELEVE:
        niveau = "élevé"
        score = min(1.0, 0.6 + 0.04 * (jours_secs - SEUIL_JOURS_SECS_ELEVE))
    elif jours_secs >= SEUIL_JOURS_SECS_MOYEN:
        niveau = "moyen"
        score = 0.35 + 0.05 * (jours_secs - SEUIL_JOURS_SECS_MOYEN)
    else:
        niveau = "faible"
        score = max(0.0, 0.25 - 0.03 * (SEUIL_JOURS_SECS_MOYEN - jours_secs))

    if valeurs_manquantes == 0:
        confiance = "élevée"
    elif valeurs_manquantes <= 5:
        confiance = "moyenne"
    else:
        confiance = "faible"

    if jours_secs > 0:
        pluriel = "s" if jours_secs > 1 else ""
        if niveau == "élevé":
            explication = (
                f"Risque élevé de poche de sécheresse, surtout à cause de {jours_secs} jour{pluriel} "
                "consécutif{s} sans pluie significative en fin de période.".format(s=pluriel)
            )
        elif niveau == "moyen":
            explication = (
                f"Risque moyen de poche de sécheresse, avec {jours_secs} jour{pluriel} "
                "consécutif{s} sans pluie significative en fin de période.".format(s=pluriel)
            )
        else:
            explication = (
                f"Risque faible de poche de sécheresse : {jours_secs} jour{pluriel} "
                "consécutif{s} sans pluie significative récemment.".format(s=pluriel)
            )
    else:
        explication = "Risque faible de poche de sécheresse : des pluies récentes ont été observées."

    return {
        "disponible": True,
        "niveau": niveau,
        "score": round(score, 2),
        "confiance": confiance,
        "source": SOURCE,
        "modele": {"nom": "règle de jours secs consécutifs", "version": "1.0-phase1"},
        "variables": {
            "jours_secs_consecutifs": jours_secs,
            "pluie_cumulee_mm": pluie_cumulee,
            "jours_analyses": len(recentes),
            "valeurs_manquantes": valeurs_manquantes,
        },
        "explication": explication,
        "a_valider_par_agronome": True,
        "date_derniere_donnee": lignes[-1][0].isoformat(),
    }
