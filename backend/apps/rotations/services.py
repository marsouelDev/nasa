"""Moteur de rotations de cultures AgroSentry (phase 3).

Compare les scénarios S0 / S1 / S2 définis dans les fixtures JSON modifiables,
score les rotations avec des pondérations sur les critères (eau, sol, revenu, travail),
et simule des scénarios climatiques de pluie (−30 % / +30 %).

Toutes les notes sont des hypothèses issues des fixtures : elles portent
`hypotheses_a_valider` et la mention « à valider avec un agronome ».
"""

from __future__ import annotations

import json
from pathlib import Path

from django.conf import settings

FICHIER_FIXTURES = Path(settings.BASE_DIR) / "fixtures" / "rotations.json"

CATEGORIE = {
    "economie_eau": "eau",
    "protection_erosion": "sol",
    "matiere_organique": "sol",
    "azote": "sol",
    "rupture_ravageurs": "revenu",
    "revenu": "revenu",
    "facilite_travail": "travail",
}
CARACTERISTIQUES = tuple(CATEGORIE)

CONF_PLAUIE_SEUIL = 0.3
CONF_ECART_SEUIL = 0.5


def charger_fixtures(chemin: Path = FICHIER_FIXTURES) -> dict:
    """Charge les fixtures JSON modifiables des rotations."""
    with open(chemin, encoding="utf-8") as fichier:
        return json.load(fichier)


def _note_final_scenario(scenario: dict, pluie_facteur: float) -> dict[str, float]:
    """Notes du critère pour la dernière culture du parcours, ajustées au climat."""
    parcours = list(scenario.get("parcours") or [])
    culture_finale = parcours[-1] if parcours else None
    notes: dict[str, float] = {}
    for note in scenario.get("notes") or []:
        if note.get("culture") != culture_finale:
            continue
        for critere, valeur in note.items():
            if critere in ("culture", "source"):
                continue
            facteur_pluie = 1.0 - pluie_facteur if CATEGORIE.get(critere) == "eau" else 1.0
            notes[critere] = float(valeur) * facteur_pluie
    return notes


def _score_pondere(notes: dict[str, float], pondations: dict, priorites: list[str]) -> tuple[float, dict]:
    """Score pondéré (0-10) : moyenne pondérée des notes des critères retenus."""
    numerateur = 0.0
    denominateur = 0.0
    contributions: dict[str, float] = {}
    for critere, note in notes.items():
        categorie = CATEGORIE.get(critere)
        if categorie not in priorites:
            continue
        poids = float(pondations.get(categorie, 0.0))
        numerateur += note * poids
        denominateur += poids
        contributions[critere] = round(note, 2)
    score = numerateur / denominateur if denominateur > 0 else 0.0
    return round(score, 2), contributions


def _confiance(scores: list[float], pluie_facteur: float) -> str:
    """Confiance : faible si écart entre scénarios ou climat extrême."""
    if abs(pluie_facteur) >= CONF_PLAUIE_SEUIL or not scores:
        return "faible"
    spread = max(scores) - min(scores)
    return "faible" if spread < CONF_ECART_SEUIL else "moyenne"


def _arguments_scenario(scenario: dict) -> dict:
    parcours = list(scenario.get("parcours") or [])
    finale = parcours[-1] if parcours else "culture de base"
    return {
        "pourquoi_proposee": (
            f"Scénario {scenario.get('id')} : rotation {', '.join(parcours) if parcours else 'hypothétique'} "
            f"après le maïs, avec pour objectif la diversification ou la protection des sols."
        ),
        "donnees_a_l_appui": [
            f"Parcours de rotation : {', '.join(parcours) if parcours else 'aucun changement'}.",
            "Notes indicatives (0-10) issues des fixtures : à valider avec un agronome.",
        ],
        "benefices": [
            f"La rotation introduit {finale}, générant un apport de diversification ou de protection des sols.",
        ],
        "lacunes_information": [
            "Notes de rotation à valider avec un agronome.",
            "Données de parcelle absentes (résolution NASA POWER ≈ 0,5°).",
        ],
        "risques_a_evaluer": [
            "Risque de pénurie hydrique si la saison s'essouffle.",
            f"Risque de rupture de cycle de culture lié à {finale}.",
        ],
    }


def construire_reponse(
    fixtures: dict | None = None,
    zone: dict | None = None,
    priorites: list[str] | None = None,
    pondations: dict | None = None,
    pluie_facteur: float | None = None,
) -> dict:
    """Construit la réponse de comparaison des scénarios de rotation."""
    fixtures = fixtures if fixtures is not None else charger_fixtures()
    priorites = (
        list(priorites) if priorites else list(fixtures.get("priorites_par_defaut") or [])
    )
    pondations = dict(pondations) if pondations else dict(fixtures.get("pondérations") or {})
    climat_actuel = {
        "id": "pluie_observee",
        "nom": "Pluie observée",
        "pluie_facteur": 0.0,
    }
    if pluie_facteur is not None:
        climat_actuel = {
            "id": "personnalisé",
            "nom": f"Pluie {pluie_facteur}",
            "pluie_facteur": float(pluie_facteur),
        }
    climatises = (
        [climat_actuel]
        if pluie_facteur is not None
        else list(fixtures.get("scénarios_climatiques") or [])
    )
    evaluations_par_scenario: list[dict] = []
    scores_par_climat: dict[float, list[float]] = {}

    resultats = []
    for scenario in fixtures.get("scénarios") or []:
        evaluations = []
        arguments = _arguments_scenario(scenario)
        for climat in climatises:
            pluie_facteur = float(climat.get("pluie_facteur") or 0.0)
            notes = _note_final_scenario(scenario, pluie_facteur)
            score, contributions = _score_pondere(notes, pondations, priorites)
            evaluations.append(
                {
                    "pluie_facteur": pluie_facteur,
                    "pluie_label": climat.get("nom") or "Pluie observée",
                    "score": score,
                    "contributions": contributions,
                }
            )
        resultats.append({"scenario": scenario, "evaluations": evaluations, "arguments": arguments})

    for resultat in resultats:
        for evaluation in resultat["evaluations"]:
            scores_par_climat.setdefault(evaluation["pluie_facteur"], []).append(evaluation["score"])
    for resultat in resultats:
        for evaluation in resultat["evaluations"]:
            evaluation["confiance"] = _confiance(
                scores_par_climat.get(evaluation["pluie_facteur"], []), evaluation["pluie_facteur"]
            )

    scenarios_out = []
    for resultat in resultats:
        scenario = resultat["scenario"]
        evaluation_actuelle = resultat["evaluations"][0]
        scenarios_out.append(
            {
                "id": scenario.get("id"),
                "nom": scenario.get("nom"),
                "parcours": list(scenario.get("parcours") or []),
                "description": scenario.get("description") or "",
                "score": evaluation_actuelle["score"],
                "contributions": evaluation_actuelle["contributions"],
                "pourquoi_proposee": resultat["arguments"]["pourquoi_proposee"],
                "donnees_a_l_appui": resultat["arguments"]["donnees_a_l_appui"],
                "benefices": resultat["arguments"]["benefices"],
                "lacunes_information": resultat["arguments"]["lacunes_information"],
                "risques_a_evaluer": resultat["arguments"]["risques_a_evaluer"],
                "confiance": evaluation_actuelle["confiance"],
                "evaluations_climatiques": [
                    {
                        "pluie_facteur": evaluation["pluie_facteur"],
                        "pluie_label": evaluation["pluie_label"],
                        "score": evaluation["score"],
                        "contributions": evaluation["contributions"],
                        "confiance": evaluation["confiance"],
                    }
                    for evaluation in resultat["evaluations"]
                ],
                "a_valider_par_agronome": True,
            }
        )

    return {
        "zone": zone,
        "source": fixtures.get("source"),
        "hypotheses_a_valider": bool(fixtures.get("hypotheses_a_valider", True)),
        "priorites": priorites,
        "pluie_facteur": climat_actuel["pluie_facteur"],
        "scenarios": scenarios_out,
    }
