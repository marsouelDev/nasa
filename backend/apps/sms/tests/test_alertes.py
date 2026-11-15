"""Tests de la tâche Celery d'alertes SMS (phase 5)."""

from __future__ import annotations

from unittest.mock import patch

from django.test import TestCase

from apps.accounts.consentement import TEXTE_CONSENTEMENT, VERSION_CONSENTEMENT
from apps.accounts.models import Agriculteur
from apps.data.models import Zone
from apps.sms.models import EnvoiSMS
from apps.sms.tasks import envoyer_alertes_risque

RISQUE = {
    "disponible": True,
    "niveau": "moyen",
    "score": 0.45,
    "confiance": "moyenne",
    "source": "test",
}


class AlertesRisqueTaskTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        Zone.objects.all().delete()
        cls.zone = Zone.objects.create(
            nom="Bafia", slug="bafia", latitude=4.75, longitude=11.23, actif=True
        )
        cls.consentant = Agriculteur(
            telephone="+237677123456", zone=cls.zone, langue="fr"
        )
        cls.consentant.accorder_consentement(TEXTE_CONSENTEMENT, VERSION_CONSENTEMENT)
        cls.consentant.save()
        cls.refusant = Agriculteur(
            telephone="+237677987654", zone=cls.zone, langue="fr"
        )
        cls.refusant.save()

    @patch("apps.sms.tasks.evaluer_risque", return_value=RISQUE)
    def test_task_prepare_un_sms_pour_chaque_consentant(self, evaluation):
        resultat = envoyer_alertes_risque.delay()
        self.assertEqual(resultat.result["alertes"], 1)
        self.assertEqual(resultat.result["envoies_crees"], 1)
        self.assertEqual(EnvoiSMS.objects.count(), 1)
        envoi = EnvoiSMS.objects.get()
        self.assertEqual(envoi.statut, EnvoiSMS.Statut.SIMULE)
        self.assertEqual(envoi.categorie, EnvoiSMS.Categorie.ALERTE_RISQUE)
        self.assertIn("Bafia", envoi.message)
        evaluation.assert_called_once()

    @patch("apps.sms.tasks.evaluer_risque", return_value=RISQUE)
    def test_task_ne_prepare_pas_pour_un_consentement_absent(self, evaluation):
        # Le consentement refusé (refusant) n'est pas filtré : seul le
        # consentant est destinataire du SMS préparé par la tâche.
        resultat = envoyer_alertes_risque.delay()
        self.assertEqual(resultat.result["alertes"], 1)
        self.assertEqual(EnvoiSMS.objects.count(), 1)
        envoi = EnvoiSMS.objects.get()
        self.assertEqual(envoi.destinataire, "+237677123456")


class AlertesEndpointTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        Zone.objects.all().delete()
        Zone.objects.create(
            nom="Bafia", slug="bafia", latitude=4.75, longitude=11.23, actif=True
        )

    @patch("apps.sms.views_alertes.envoyer_alertes_risque")
    def test_endpoint_declenche_la_tache(self, task):
        task.delay.return_value = {"zones": [], "alertes": 0, "envoies_crees": 0, "ignores": []}
        reponse = self.client.post("/api/sms/alertes/")
        self.assertEqual(reponse.status_code, 200)
        self.assertEqual(task.delay.call_count, 1)
        corps = reponse.json()
        self.assertEqual(corps["resultat"]["alertes"], 0)
        task.delay.assert_called_once_with(None)
