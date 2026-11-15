"""Tests du service ML : features, entraînement et prédiction (aucun réseau)."""

from datetime import date, timedelta
from pathlib import Path
from tempfile import TemporaryDirectory

from django.test import SimpleTestCase

from apps.ml import services

DEBUT = date(2026, 1, 1)


def serie_energiee(jours: int = 150, pluies_par_jour: list[float] | None = None) -> list[tuple]:
    """Série journalière synthétique (pluie en mm/jour, températures en °C)."""
    pluies = pluies_par_jour if pluies_par_jour is not None else [0.0] * jours
    lignes = []
    for decalage in range(jours):
        lignes.append(
            (DEBUT + timedelta(days=decalage), pluies[decalage], 25.0 + 5.0 * ((decalage % 7) / 7.0), 20.0)
        )
    return lignes


class ConstruireTableauTests(SimpleTestCase):
    def test_les_colonnes_explicatives_existent(self):
        dataframe = services.construire_dataframe(serie_energiee(60))
        for colonne in services.COLONNES:
            self.assertIn(colonne, dataframe.columns)
        self.assertIn("target", dataframe.columns)

    def test_jeu_entrainement_supprime_les_lignes_incompletees(self):
        dataframe = services.construire_dataframe(serie_energiee(40))
        X, y = services.jeu_entrainement(dataframe)
        self.assertGreater(len(X), 0)
        self.assertGreater(len(y), 0)


class EntrainementTests(SimpleTestCase):
    def test_entrainer_retourne_un_artefact(self):
        dataframe = services.construire_dataframe(serie_energiee(150))
        artefact = services.entrainer(dataframe)
        self.assertIn("modèle", artefact)
        self.assertIn("precision_cv_balanced_accuracy", artefact)
        self.assertIn("variables_importantes", artefact)
        precision = artefact["precision_cv_balanced_accuracy"]
        self.assertGreaterEqual(precision, 0.0)
        self.assertLessEqual(precision, 1.0)
        self.assertEqual(sorted(artefact["variables_importantes"]), sorted(services.COLONNES))


class PredireTests(SimpleTestCase):
    def test_predire_retourne_le_format_de_la_reponse(self):
        lignes = serie_energiee(150)
        artefact = services.entrainer(services.construire_dataframe(lignes))
        resultat = services.predire(artefact, lignes)

        self.assertTrue(resultat["disponible"])
        self.assertIn(resultat["niveau"], ("faible", "moyen", "élevé"))
        self.assertIsInstance(resultat["score"], float)
        self.assertIn(resultat["confiance"], ("faible", "moyenne", "élevée"))
        self.assertIn("Random Forest", resultat["source"])
        self.assertTrue(resultat["a_valider_par_agronome"])
        self.assertIn("cible", resultat["prediction"])
        self.assertIn("probabilites", resultat["prediction"])
        self.assertIn("explication", resultat)
        self.assertEqual(resultat["prediction"]["cible"], f"poche de sécheresse dans les 15 prochains jours")

    def test_sauvegarder_et_charger(self):
        lignes = serie_energiee(150)
        artefact = services.entrainer(services.construire_dataframe(lignes))
        with TemporaryDirectory() as dossier:
            chemin = Path(dossier) / "modele.joblib"
            services.sauvegarder(artefact, chemin)
            chargé = services.charger(chemin)
            self.assertIsNotNone(chargé)
            self.assertIsNotNone(chargé["modèle"])

    def test_charger_un_modele_absent(self):
        self.assertIsNone(services.charger(Path("in/existant/inexistant.joblib")))
