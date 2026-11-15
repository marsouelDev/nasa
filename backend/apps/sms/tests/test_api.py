"""Tests de l'API SMS simulée et du journal (phase 5)."""

from __future__ import annotations

import json
from unittest.mock import patch

from django.test import TestCase

from apps.accounts.consentement import TEXTE_CONSENTEMENT, VERSION_CONSENTEMENT
from apps.accounts.models import Agriculteur
from apps.data.models import Zone
from apps.sms.models import EnvoiSMS

RISQUE = {
    "disponible": True,
    "niveau": "moyen",
    "score": 0.45,
    "confiance": "moyenne",
    "source": "test",
}


class SimulateurSMSTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        Zone.objects.all().delete()
        cls.zone = Zone.objects.create(
            nom="Bafia", slug="bafia", latitude=4.75, longitude=11.23, actif=True
        )

    def creer_agriculteur(self, *, consentement: bool = True, telephone: str = "+237677123456"):
        agriculteur = Agriculteur(telephone=telephone, zone=self.zone, langue="fr")
        if consentement:
            agriculteur.accorder_consentement(TEXTE_CONSENTEMENT, VERSION_CONSENTEMENT)
        agriculteur.save()
        return agriculteur

    def poster(self, donnees: dict):
        return self.client.post(
            "/api/sms/simuler/", data=json.dumps(donnees), content_type="application/json"
        )

    def test_numero_non_inscrit_refuse(self):
        reponse = self.poster({"telephone": "699999999", "message": "Bonjour"})
        self.assertEqual(reponse.status_code, 400)
        self.assertTrue(reponse.json()["consentement_requis"])
        self.assertEqual(EnvoiSMS.objects.count(), 0)

    def test_inscrit_sans_consentement_refuse(self):
        self.creer_agriculteur(consentement=False)
        reponse = self.poster({"telephone": "677123456", "message": "Bonjour"})
        self.assertEqual(reponse.status_code, 403)
        self.assertEqual(reponse.json()["etat"], "sans consentement")
        self.assertEqual(EnvoiSMS.objects.count(), 0)

    def test_inscrit_desinscrit_refuse(self):
        agriculteur = self.creer_agriculteur()
        agriculteur.retirer_consentement()
        agriculteur.save()
        reponse = self.poster({"telephone": "677123456", "message": "Bonjour"})
        self.assertEqual(reponse.status_code, 403)
        self.assertIn("désinscrit", reponse.json()["etat"])
        self.assertEqual(EnvoiSMS.objects.count(), 0)

    def test_envoi_simule_avec_message_personnalise(self):
        self.creer_agriculteur()
        reponse = self.poster(
            {"telephone": "+237 677 12 34 56", "message": "Alerte de test AgroSentry."}
        )
        self.assertEqual(reponse.status_code, 201)
        corps = reponse.json()
        self.assertTrue(corps["simulation"])
        self.assertEqual(corps["sms"]["statut"], "simule")
        self.assertEqual(corps["sms"]["mode"], "simulation")
        self.assertEqual(corps["sms"]["telephone_masque"], "+2376••••••56")
        self.assertNotIn("+237677123456", reponse.content.decode())
        self.assertEqual(EnvoiSMS.objects.count(), 1)
        self.assertIn("rien n'a été transmis", corps["message_utilisateur"])

    @patch("apps.sms.views.evaluer_risque", return_value=RISQUE)
    def test_message_par_defaut_depuis_le_risque(self, evaluation):
        self.creer_agriculteur()
        reponse = self.poster({"telephone": "677123456"})
        self.assertEqual(reponse.status_code, 201)
        corps = reponse.json()
        self.assertLessEqual(corps["sms"]["longueur"], 160)
        self.assertIn("Bafia", corps["sms"]["message"])
        self.assertIn("confiance moyenne", corps["sms"]["message"])
        self.assertIn("agronome", corps["sms"]["message"])
        evaluation.assert_called_once()

    @patch("apps.sms.views.evaluer_risque", return_value={"disponible": False})
    def test_message_par_defaut_sans_donnees(self, evaluation):
        self.creer_agriculteur()
        reponse = self.poster({"telephone": "677123456"})
        self.assertEqual(reponse.status_code, 400)
        self.assertEqual(EnvoiSMS.objects.count(), 0)

    def test_message_trop_long_refuse(self):
        self.creer_agriculteur()
        reponse = self.poster({"telephone": "677123456", "message": "x" * 161})
        self.assertEqual(reponse.status_code, 400)
        self.assertIn("160", reponse.json()["detail"])
        self.assertEqual(EnvoiSMS.objects.count(), 0)

    def test_numero_invalide(self):
        reponse = self.poster({"telephone": "abc", "message": "Bonjour"})
        self.assertEqual(reponse.status_code, 400)
        self.assertIn("telephone", reponse.json())
        self.assertEqual(EnvoiSMS.objects.count(), 0)


class JournalSMSTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        Zone.objects.all().delete()
        cls.zone = Zone.objects.create(
            nom="Bafia", slug="bafia", latitude=4.75, longitude=11.23, actif=True
        )
        cls.agriculteur = Agriculteur(telephone="+237677123456", zone=cls.zone)
        cls.agriculteur.accorder_consentement(TEXTE_CONSENTEMENT, VERSION_CONSENTEMENT)
        cls.agriculteur.save()
        EnvoiSMS.objects.create(
            agriculteur=cls.agriculteur,
            destinataire=cls.agriculteur.telephone,
            message="Premier message",
            longueur=15,
            statut=EnvoiSMS.Statut.SIMULE,
            mode=EnvoiSMS.Mode.SIMULATION,
            categorie=EnvoiSMS.Categorie.TEST,
        )
        EnvoiSMS.objects.create(
            agriculteur=cls.agriculteur,
            destinataire=cls.agriculteur.telephone,
            message="Deuxième message",
            longueur=15,
            statut=EnvoiSMS.Statut.SIMULE,
            mode=EnvoiSMS.Mode.SIMULATION,
            categorie=EnvoiSMS.Categorie.ALERTE_RISQUE,
        )

    def test_journal_masque_et_limite(self):
        reponse = self.client.get("/api/sms/journal/", {"limite": 1})
        self.assertEqual(reponse.status_code, 200)
        corps = reponse.json()
        self.assertTrue(corps["simulation"])
        self.assertEqual(corps["longueur_max"], 160)
        self.assertEqual(len(corps["envois"]), 1)
        self.assertEqual(corps["envois"][0]["telephone_masque"], "+2376••••••56")
        self.assertNotIn("+237677123456", reponse.content.decode())

    def test_journal_limite_invalide(self):
        reponse = self.client.get("/api/sms/journal/", {"limite": 0})
        self.assertEqual(reponse.status_code, 400)


class ApercuSMSTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        Zone.objects.all().delete()
        Zone.objects.create(
            nom="Bafia", slug="bafia", latitude=4.75, longitude=11.23, actif=True
        )

    @patch("apps.sms.views.evaluer_risque", return_value=RISQUE)
    def test_apercu_sans_destinataire(self, evaluation):
        reponse = self.client.get("/api/sms/apercu/", {"zone": "bafia"})
        self.assertEqual(reponse.status_code, 200)
        corps = reponse.json()
        self.assertLessEqual(corps["longueur"], 160)
        self.assertIn("agronome", corps["message"])
        self.assertTrue(corps["simulation"])
        self.assertEqual(EnvoiSMS.objects.count(), 0)

    def test_zone_inconnue(self):
        reponse = self.client.get("/api/sms/apercu/", {"zone": "inconnue"})
        self.assertEqual(reponse.status_code, 404)
