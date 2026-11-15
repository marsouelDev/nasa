"""Tests des endpoints de l'API rotations (phase 3)."""

from django.test import TestCase

from apps.data.models import Zone


class RotationsApiTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        Zone.objects.all().delete()
        cls.zone = Zone.objects.create(
            nom="Bafia",
            slug="bafia",
            latitude=4.75,
            longitude=11.23,
            actif=True,
        )

    def test_index_rotations(self):
        reponse = self.client.get("/api/rotations/")
        self.assertEqual(reponse.status_code, 200)
        donnees = reponse.json()
        self.assertEqual(len(donnees["scenarios"]), 3)
        self.assertEqual(donnees["priorites"], ["eau", "sol", "revenu", "travail"])
        self.assertEqual(donnees["pluie_facteur"], 0.0)
        self.assertTrue(donnees["hypotheses_a_valider"])

    def test_priorites_personnalisees(self):
        reponse = self.client.get("/api/rotations/", {"priorites": "eau,travail"})
        self.assertEqual(reponse.status_code, 200)
        self.assertEqual(reponse.json()["priorites"], ["eau", "travail"])

    def test_pluie_personnalise(self):
        reponse = self.client.get("/api/rotations/", {"pluie": -0.3})
        self.assertEqual(reponse.status_code, 200)
        donnees = reponse.json()
        self.assertEqual(donnees["pluie_facteur"], -0.3)
        self.assertEqual(donnees["scenarios"][0]["evaluations_climatiques"][0]["pluie_facteur"], -0.3)

    def test_pondations_personnalisees(self):
        reponse = self.client.get(
            "/api/rotations/", {"pondations": "eau=0.5,sol=0.2,revenu=0.0,travail=0.3"}
        )
        self.assertEqual(reponse.status_code, 200)
        score_s0 = reponse.json()["scenarios"][0]["score"]
        # Score différent des pondérations par défaut (eau 0,30 · sol 0,20 · revenu 0,20 · travail 0,20).
        self.assertNotEqual(score_s0, 4.73)
        # Moyenne pondérée : (5*0.5 + 6*0.2 + 3*0.2 + 2*0.2 + 4*0.0 + 6*0.0 + 7*0.3) / (0.5+0.6+0.3) = 4.86
        self.assertEqual(score_s0, 4.86)

    def test_scenarios_contiennent_les_rubriques(self):
        reponse = self.client.get("/api/rotations/")
        for scenario in reponse.json()["scenarios"]:
            self.assertIn("score", scenario)
            self.assertIn("contributions", scenario)
            self.assertIn("pourquoi_proposee", scenario)
            self.assertIn("donnees_a_l_appui", scenario)
            self.assertIn("benefices", scenario)
            self.assertIn("lacunes_information", scenario)
            self.assertIn("risques_a_evaluer", scenario)
            self.assertIn("confiance", scenario)
