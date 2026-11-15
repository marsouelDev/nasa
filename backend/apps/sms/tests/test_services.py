"""Tests du service SMS : consentement, longueur, simulation (phase 5)."""

from __future__ import annotations

from unittest.mock import Mock, patch

import requests
from django.test import TestCase, override_settings

from apps.accounts.consentement import TEXTE_CONSENTEMENT, VERSION_CONSENTEMENT
from apps.accounts.models import Agriculteur
from apps.data.models import Zone
from apps.sms.models import EnvoiSMS
from apps.sms.services import (
    ConsentementManquant,
    MessageSMSInvalide,
    construire_sms_risque,
    envoyer_sms,
    simulation_active,
)

RISQUE_ELEVE = {
    "disponible": True,
    "niveau": "élevé",
    "score": 0.82,
    "confiance": "moyenne",
    "source": "test",
}


class ConstruireMessageTests(TestCase):
    def test_message_risque_borne_et_complet(self):
        message = construire_sms_risque("Bafia", RISQUE_ELEVE)
        self.assertLessEqual(len(message), 160)
        self.assertIn("Bafia", message)
        self.assertIn("ÉLEVÉ", message)
        self.assertIn("confiance moyenne", message)
        self.assertIn("agronome", message)
        self.assertIn("STOP", message)

    def test_message_risque_indisponible(self):
        message = construire_sms_risque("Bafia", {"disponible": False})
        self.assertLessEqual(len(message), 160)
        self.assertIn("indisponibles", message)
        self.assertIn("agronome", message)

    def test_message_anglais(self):
        message = construire_sms_risque("Bafia", RISQUE_ELEVE, langue="en")
        self.assertLessEqual(len(message), 160)
        self.assertIn("HIGH", message)
        self.assertIn("agronomist", message)
        self.assertIn("STOP", message)

    def test_nom_de_zone_long_tronque(self):
        message = construire_sms_risque("Z" * 200, RISQUE_ELEVE)
        self.assertLessEqual(len(message), 160)


class EnvoiSMSTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        Zone.objects.all().delete()
        cls.zone = Zone.objects.create(
            nom="Bafia", slug="bafia", latitude=4.75, longitude=11.23, actif=True
        )

    def creer_agriculteur(self, *, consentement: bool = True) -> Agriculteur:
        agriculteur = Agriculteur(
            telephone="+237677123456", zone=self.zone, langue="fr"
        )
        if consentement:
            agriculteur.accorder_consentement(TEXTE_CONSENTEMENT, VERSION_CONSENTEMENT)
        agriculteur.save()
        return agriculteur

    def test_refus_sans_consentement(self):
        agriculteur = self.creer_agriculteur(consentement=False)
        with self.assertRaises(ConsentementManquant):
            envoyer_sms(agriculteur, "Message de test")
        self.assertEqual(EnvoiSMS.objects.count(), 0)

    def test_refus_apres_desinscription(self):
        agriculteur = self.creer_agriculteur()
        agriculteur.retirer_consentement()
        agriculteur.save()
        with self.assertRaises(ConsentementManquant):
            envoyer_sms(agriculteur, "Message de test")
        self.assertEqual(EnvoiSMS.objects.count(), 0)

    def test_message_trop_long_refuse_sans_trace(self):
        agriculteur = self.creer_agriculteur()
        with self.assertRaises(MessageSMSInvalide):
            envoyer_sms(agriculteur, "x" * 161)
        self.assertEqual(EnvoiSMS.objects.count(), 0)

    def test_message_vide_refuse(self):
        agriculteur = self.creer_agriculteur()
        with self.assertRaises(MessageSMSInvalide):
            envoyer_sms(agriculteur, "   ")
        self.assertEqual(EnvoiSMS.objects.count(), 0)

    def test_simulation_par_defaut(self):
        agriculteur = self.creer_agriculteur()
        envoi = envoyer_sms(agriculteur, "AgroSentry : test simulé.")
        self.assertEqual(envoi.statut, EnvoiSMS.Statut.SIMULE)
        self.assertEqual(envoi.mode, EnvoiSMS.Mode.SIMULATION)
        self.assertEqual(envoi.longueur, len("AgroSentry : test simulé."))
        self.assertEqual(envoi.destinataire, "+237677123456")
        self.assertEqual(envoi.reference, "")
        self.assertTrue(simulation_active())

    @override_settings(SMS_SIMULATION=False, SMS_ENVOI_REEL=False, AT_USERNAME="demo", AT_API_KEY="cle-test")
    def test_cles_sans_opt_in_reel_restent_simulees(self):
        self.assertTrue(simulation_active())
        agriculteur = self.creer_agriculteur()
        envoi = envoyer_sms(agriculteur, "Toujours simulé.")
        self.assertEqual(envoi.statut, EnvoiSMS.Statut.SIMULE)

    @override_settings(
        SMS_SIMULATION=False,
        SMS_ENVOI_REEL=True,
        AT_USERNAME="demo",
        AT_API_KEY="cle-test",
    )
    @patch("apps.sms.services.requests.post")
    def test_mode_reel_appelle_la_passerelle(self, post: Mock):
        post.return_value.json.return_value = {
            "SMSMessageData": {
                "Recipients": [
                    {"statusCode": 101, "status": "Success", "messageId": "ATXid_123"}
                ]
            }
        }
        self.assertFalse(simulation_active())
        agriculteur = self.creer_agriculteur()
        envoi = envoyer_sms(agriculteur, "Message réel de test.")
        self.assertEqual(post.call_count, 1)
        corps = post.call_args.kwargs["data"]
        self.assertEqual(corps["to"], "+237677123456")
        self.assertEqual(corps["username"], "demo")
        self.assertEqual(envoi.statut, EnvoiSMS.Statut.ENVOYE)
        self.assertEqual(envoi.mode, EnvoiSMS.Mode.REEL)
        self.assertEqual(envoi.reference, "ATXid_123")

    @override_settings(
        SMS_SIMULATION=False,
        SMS_ENVOI_REEL=True,
        AT_USERNAME="demo",
        AT_API_KEY="cle-test",
    )
    @patch("apps.sms.services.requests.post")
    def test_echec_operateur_journalise(self, post: Mock):
        post.return_value.json.return_value = {
            "SMSMessageData": {
                "Recipients": [
                    {"statusCode": 402, "status": "Invalid Phone Number"}
                ]
            }
        }
        agriculteur = self.creer_agriculteur()
        envoi = envoyer_sms(agriculteur, "Message en échec.")
        self.assertEqual(envoi.statut, EnvoiSMS.Statut.ECHEC)
        self.assertIn("Invalid Phone Number", envoi.erreur)

    @override_settings(
        SMS_SIMULATION=False,
        SMS_ENVOI_REEL=True,
        AT_USERNAME="demo",
        AT_API_KEY="cle-test",
    )
    @patch("apps.sms.services.requests.post", side_effect=requests.ConnectionError("réseau"))
    def test_erreur_reseau_journalisee(self, post: Mock):
        agriculteur = self.creer_agriculteur()
        envoi = envoyer_sms(agriculteur, "Message en échec réseau.")
        self.assertEqual(envoi.statut, EnvoiSMS.Statut.ECHEC)
        self.assertIn("réseau", envoi.erreur)
