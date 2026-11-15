"""Tests de la règle de risque de poche de sécheresse."""

from datetime import date, timedelta

from django.test import SimpleTestCase

from apps.data.services import risk

DEBUT = date(2026, 1, 1)


def serie(jours: int, pluie: float = 0.0, debut: date = DEBUT) -> list[tuple[date, float]]:
    return [(debut + timedelta(days=i), pluie) for i in range(jours)]


def suite(*blocs: tuple[int, float]) -> list[tuple[date, float]]:
    """Construit une série continue à partir de blocs (nombre de jours, pluie)."""
    lignes: list[tuple[date, float]] = []
    for jours, pluie in blocs:
        debut = DEBUT + timedelta(days=len(lignes))
        lignes.extend(serie(jours, pluie, debut))
    return lignes


class JoursSecsTests(SimpleTestCase):
    def test_compte_les_jours_secs_en_fin_de_serie(self):
        lignes = suite((10, 0.0), (1, 5.0), (3, 0.0))
        self.assertEqual(risk.jours_secs_consecutifs(lignes), 3)

    def test_valeur_manquante_en_fin_interrompt_le_decompte(self):
        lignes = suite((3, 0.0))
        lignes.append((DEBUT + timedelta(days=3), None))
        self.assertEqual(risk.jours_secs_consecutifs(lignes), 0)

    def test_valeur_manquante_au_milieu_arrete_le_decompte(self):
        lignes = suite((3, 0.0))
        lignes.append((DEBUT + timedelta(days=3), None))
        lignes.extend(serie(2, 0.0, DEBUT + timedelta(days=4)))
        self.assertEqual(risk.jours_secs_consecutifs(lignes), 2)


class AssessTests(SimpleTestCase):
    def test_risque_eleve_apres_douze_jours_secs(self):
        resultat = risk.assess(suite((30, 0.0)))
        self.assertEqual(resultat["niveau"], "élevé")
        self.assertEqual(resultat["confiance"], "élevée")
        self.assertTrue(resultat["a_valider_par_agronome"])
        self.assertIn("règle", resultat["source"])

    def test_risque_moyen(self):
        resultat = risk.assess(suite((20, 0.0), (1, 10.0), (7, 0.0)))
        self.assertEqual(resultat["niveau"], "moyen")

    def test_risque_faible_apres_une_pluie_recente(self):
        resultat = risk.assess(suite((28, 0.0), (1, 12.0), (1, 3.0)))
        self.assertEqual(resultat["niveau"], "faible")

    def test_valeurs_manquantes_reduisent_la_confiance(self):
        lignes = suite((30, 0.0))
        lignes = [
            (jour, None) if index < 10 else (jour, pluie)
            for index, (jour, pluie) in enumerate(lignes)
        ]
        resultat = risk.assess(lignes)
        self.assertEqual(resultat["niveau"], "élevé")
        self.assertEqual(resultat["confiance"], "faible")

    def test_serie_vide(self):
        resultat = risk.assess([])
        self.assertFalse(resultat["disponible"])
        self.assertEqual(resultat["confiance"], "faible")
