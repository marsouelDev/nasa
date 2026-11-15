"""Tests du moteur de rotations (phase 3) : fixtures, score, climat."""

from django.test import SimpleTestCase

from apps.rotations import services

PRIORITES_DEFAUT = ["eau", "sol", "revenu", "travail"]


class FixturesTests(SimpleTestCase):
    def test_fixtures_sont_chargees(self):
        fixtures = services.charger_fixtures()
        self.assertEqual(fixtures["version"], "1.0-phase3")
        self.assertTrue(fixtures["hypotheses_a_valider"])
        self.assertEqual(len(fixtures["scénarios"]), 3)
        self.assertEqual(
            [scenario["id"] for scenario in fixtures["scénarios"]],
            ["S0", "S1", "S2"],
        )
        self.assertEqual(
            len(fixtures["scénarios_climatiques"]), 3,
        )

    def test_fixtures_contiennent_les_critères_cles(self):
        fixtures = services.charger_fixtures()
        notes = fixtures["scénarios"][0]["notes"]
        critères = set(notes[0].keys()) - {"culture", "source"}
        self.assertEqual(
            sorted(critères),
            sorted(
                [
                    "economie_eau",
                    "protection_erosion",
                    "matiere_organique",
                    "azote",
                    "rupture_ravageurs",
                    "revenu",
                    "facilite_travail",
                ]
            ),
        )


class ScoreTests(SimpleTestCase):
    def test_score_pondore_de_la_rotation_actuelle(self):
        reponse = services.construire_reponse(
            fixtures=services.charger_fixtures(), priorites=PRIORITES_DEFAUT
        )
        score_s0 = reponse["scenarios"][0]["score"]
        # Moyenne pondérée des notes (eau 0,30 · sol 0,20 · revenu 0,20 · travail 0,20).
        self.assertEqual(score_s0, 4.73)

    def test_score_des_scenarios_s1_et_s2(self):
        reponse = services.construire_reponse(
            fixtures=services.charger_fixtures(), priorites=PRIORITES_DEFAUT
        )
        self.assertEqual(reponse["scenarios"][1]["score"], 6.4)
        self.assertEqual(reponse["scenarios"][2]["score"], 5.73)

    def test_scenario_s0_est_la_reference(self):
        reponse = services.construire_reponse(
            fixtures=services.charger_fixtures(), priorites=PRIORITES_DEFAUT
        )
        self.assertEqual(reponse["scenarios"][0]["id"], "S0")
        self.assertEqual(reponse["scenarios"][0]["parcours"], ["maïs"])


class ClimTests(SimpleTestCase):
    def test_scenario_pluie_moins_de_trente_pourcent(self):
        fixtures = services.charger_fixtures()
        reponse = services.construire_reponse(fixtures=fixtures, priorites=PRIORITES_DEFAUT)
        evaluations = reponse["scenarios"][0]["evaluations_climatiques"]
        self.assertEqual(evaluations[0]["pluie_facteur"], 0.0)
        self.assertEqual(evaluations[1]["pluie_facteur"], -0.3)
        self.assertEqual(evaluations[2]["pluie_facteur"], 0.3)
        # Pluie −30 % : l'économie d'eau devient plus valorisée (note ajustée).
        self.assertNotEqual(evaluations[1]["score"], evaluations[0]["score"])


class RubriquesTests(SimpleTestCase):
    def test_chaque_scenario_contient_les_rubriques_obligatoires(self):
        reponse = services.construire_reponse(
            fixtures=services.charger_fixtures(), priorites=PRIORITES_DEFAUT
        )
        obligatoires = (
            "score",
            "contributions",
            "pourquoi_proposee",
            "donnees_a_l_appui",
            "benefices",
            "lacunes_information",
            "risques_a_evaluer",
            "confiance",
            "evaluations_climatiques",
            "a_valider_par_agronome",
        )
        for scenario in reponse["scenarios"]:
            for rubrique in obligatoires:
                self.assertIn(rubrique, scenario, f"Scénario {scenario.get('id')} sans rubrique {rubrique}")

    def test_confiance_valide(self):
        reponse = services.construire_reponse(
            fixtures=services.charger_fixtures(), priorites=PRIORITES_DEFAUT
        )
        for scenario in reponse["scenarios"]:
            self.assertIn(scenario["confiance"], ("faible", "moyenne"))
            self.assertTrue(scenario["a_valider_par_agronome"])
        self.assertTrue(reponse["hypotheses_a_valider"])
