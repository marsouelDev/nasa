"""Service de modélisation AgroSentry : Random Forest du risque de sécheresse.

Port de `agrosentry_model.py` : construction des variables explicables à partir
des séries journalières NASA POWER stockées en base, entraînement du Random
Forest avec validation temporelle, et prédiction.

Aucune donnée n'est inventée : les variables sont des agrégats observés
(cumul de pluie, moyenne de température, jours secs).
"""

from __future__ import annotations

from datetime import date
from pathlib import Path

import joblib
import pandas as pd
from django.conf import settings
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import TimeSeriesSplit, cross_val_score

SEUIL_PLUIE_SECHE_MM = 1.0
SEUIL_JOURS_SECS_ELEVE = 10
FENETRE_TARGET_JOURS = 15
SEUIL_PREDICTION_ELEVE = 0.66
SEUIL_PREDICTION_MOYEN = 0.33

SOURCE_MODELE_PHASE2 = "Random Forest entraîné sur les données NASA POWER (phase 2)"
VERSION_MODELE = "1.0-phase2"

COLONNES = ("rain7", "rain30", "tmax7", "dry_days14", "doy")
CHEMIN_MODELE = Path(settings.BASE_DIR) / "ml" / "risque_secheresse.joblib"


def construire_dataframe(
    lignes: list[tuple[date, float | None, float | None, float | None]],
) -> pd.DataFrame:
    """Construit le tableau pandas à partir des observations journalières.

    `lignes` : série journalière triée par date, tuples
    (date, precip_mm, tmax_c, tmin_c).
    """
    pluies = [float(valeur) if valeur is not None else float("nan") for _, valeur, _, _ in lignes]
    temperatures = [
        float(valeur) if valeur is not None else float("nan") for _, _, valeur, _ in lignes
    ]
    dataframe = pd.DataFrame(
        {"date": pd.to_datetime([jour for jour, *_ in lignes]), "rain": pluies, "tmax": temperatures}
    ).set_index("date")

    dataframe["rain7"] = dataframe["rain"].rolling(7).sum()
    dataframe["rain30"] = dataframe["rain"].rolling(30).sum()
    dataframe["tmax7"] = dataframe["tmax"].rolling(7).mean()
    dataframe["dry_days14"] = (dataframe["rain"] < SEUIL_PLUIE_SECHE_MM).astype(int).rolling(14).sum()
    dataframe["doy"] = dataframe.index.dayofyear

    pluies_manquantes = (dataframe["rain"] < SEUIL_PLUIE_SECHE_MM).astype(int)
    dataframe["target"] = (
        pluies_manquantes.shift(-1).rolling(FENETRE_TARGET_JOURS).sum() >= SEUIL_JOURS_SECS_ELEVE
    ).astype(int)

    return dataframe


def jeu_entrainement(dataframe: pd.DataFrame) -> tuple[pd.DataFrame, pd.Series]:
    """Prépare (X, y) propres : colonnes explicatives complètes, cible connue."""
    colonnes = (*COLONNES, "target")
    jeu = dataframe.dropna(subset=list(colonnes))
    return jeu[list(COLONNES)], jeu["target"]


def entrainer(jeu: pd.DataFrame) -> dict:
    """Entraîne le Random Forest avec validation temporelle (TimeSeriesSplit)."""
    X, y = jeu_entrainement(jeu)
    modele = RandomForestClassifier(
        n_estimators=200,
        max_depth=8,
        min_samples_leaf=10,
        class_weight="balanced",
        random_state=0,
    )
    cv = TimeSeriesSplit(n_splits=5, gap=15)
    scores = cross_val_score(modele, X, y, cv=cv, scoring="balanced_accuracy")
    precision = float(scores.mean())
    modele.fit(X, y)
    importances = {
        colonne: float(poids) for colonne, poids in zip(X.columns, modele.feature_importances_)
    }
    return {
        "modèle": modele,
        "precision_cv_balanced_accuracy": precision,
        "nb_jours_entrainement": int(len(jeu)),
        "variables_importantes": importances,
    }


def sauvegarder(artefact: dict, chemin: Path = CHEMIN_MODELE) -> str:
    """Sauvegarde l'artefact (modèle + métadonnées) au format joblib."""
    chemin.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(artefact, chemin)
    return str(chemin)


def charger(chemin: Path = CHEMIN_MODELE) -> dict | None:
    """Charge l'artefact entraîné ; retourne None s'il n'existe pas encore."""
    if not chemin.exists():
        return None
    return joblib.load(chemin)


def _confiance(artefact: dict) -> str:
    """Traduit la performance de validation temporelle en niveau de confiance."""
    precision = artefact.get("precision_cv_balanced_accuracy", 0.0)
    if precision >= 0.7:
        return "élevée"
    if precision >= 0.5:
        return "moyenne"
    return "faible"


def predire(artefact: dict, lignes: list[tuple[date, float | None, float | None, float | None]]) -> dict:
    """Prophétise une poche de sécheresse à partir des données disponibles."""
    modele = artefact["modèle"]
    dataframe = construire_dataframe(lignes)
    jeu = dataframe.dropna(subset=(*COLONNES, "target"))
    X = jeu[list(COLONNES)]
    derniere = X.iloc[-1]
    probabilites = modele.predict_proba(X.iloc[[-1]])[0]
    classes = [int(c) for c in modele.classes_]
    indice_poche = classes.index(1) if 1 in classes else len(classes) - 1
    proba_poche = float(probabilites[indice_poche])
    score = round(proba_poche, 2)
    niveau = (
        "élevé" if score >= SEUIL_PREDICTION_ELEVE else "moyen" if score >= SEUIL_PREDICTION_MOYEN else "faible"
    )
    variables = {colonne: float(derniere[colonne]) for colonne in COLONNES}
    ordre = sorted(COLONNES, key=lambda colonne: -artefact["variables_importantes"][colonne])
    contributeurs = ", ".join(f"{colonne} ({variables[colonne]:.2f})" for colonne in ordre[:3])
    explication = (
        f"Le modèle prédit une poche de sécheresse dans les {FENETRE_TARGET_JOURS} prochains jours "
        f"avec une probabilité de {score}. Variables explicatives les plus influentes : {contributeurs}."
    )

    return {
        "disponible": True,
        "niveau": niveau,
        "score": score,
        "confiance": _confiance(artefact),
        "source": SOURCE_MODELE_PHASE2,
        "modele": {
            "nom": "RandomForestClassifier",
            "version": VERSION_MODELE,
            "precision_cv_balanced_accuracy": artefact.get("precision_cv_balanced_accuracy"),
        },
        "variables": variables,
        "prediction": {
            "cible": f"poche de sécheresse dans les {FENETRE_TARGET_JOURS} prochains jours",
            "probabilites": {
                "poche_secheresse": score,
                "aucune_poche": round(1.0 - proba_poche, 2),
            },
        },
        "explication": explication,
        "a_valider_par_agronome": True,
        "date_derniere_donnee": lignes[-1][0].isoformat(),
    }
