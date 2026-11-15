"""Tests du moteur et des endpoints USSD simulés (phase 5)."""

from __future__ import annotations

import json
from datetime import date, timedelta
from unittest.mock import patch

from django.test import TestCase

from apps.data.models import DailyWeather, Zone
from apps.sms import ussd

RISQUE = {
    "disponible": True,
    "niveau": "élevé",
    "score": 0.82,
    "confiance": "moyenne",
    "source": "test",
    "date_derniere_donnee": "2026-11-15",
}


class UssdMoteurTests(TestCase):
    def test_menu_principal(self):
        reponse = ussd.traiter("", zone_nom="Bafia")
        self.assertTrue(reponse.startswith("CON "))
        self.assertIn("1: risque", reponse)
        self.assertIn("2: pluie 30j", reponse)
        self.assertIn("3: semis", reponse)
        self.assertIn("4: quitter", reponse)
        self.assertLessEqual(len(reponse), 182)

    def test_risque_disponible(self):
        reponse = ussd.traiter("1", zone_nom="Bafia", risque=RISQUE)
        self.assertTrue(reponse.startswith("CON "))
        self.assertIn("ÉLEVÉ", reponse)
        self.assertIn("confiance moyenne", reponse)
        self.assertIn("agronome", reponse.lower())
        self.assertLessEqual(len(reponse), 182)

    def test_risque_indisponible(self):
        reponse = ussd.traiter("1", zone_nom="Bafia", risque={"disponible": False})
        self.assertIn("indisponibles", reponse.lower())
        self.assertLessEqual(len(reponse), 182)

    def test_pluie(self):
        reponse = ussd.traiter("2", zone_nom="Bafia", pluie_30j=42.5)
        self.assertIn("42.5 mm", reponse)
        self.assertLessEqual(len(reponse), 182)

    def test_pluie_indisponible(self):
        reponse = ussd.traiter("2", zone_nom="Bafia", pluie_30j=None)
        self.assertIn("indisponible", reponse.lower())
        self.assertLessEqual(len(reponse), 182)

    def test_semis(self):
        fenetre = {"debut": "2026-03-15", "fin": "2026-03-25"}
        reponse = ussd.traiter("3", zone_nom="Bafia", fenetre_semis=fenetre)
        self.assertIn("2026-03-15", reponse)
        self.assertIn("2026-03-25", reponse)
        self.assertIn("agronome", reponse.lower())
        self.assertLessEqual(len(reponse), 182)

    def test_semis_indisponible(self):
        reponse = ussd.traiter("3", zone_nom="Bafia", fenetre_semis=None)
        self.assertIn("indisponible", reponse.lower())
        self.assertLessEqual(len(reponse), 182)

    def test_quitter(self):
        reponse = ussd.traiter("4", zone_nom="Bafia")
        self.assertTrue(reponse.startswith("END "))
        self.assertIn("STOP", reponse)
        self.assertLessEqual(len(reponse), 182)

    def test_option_inconnue(self):
        reponse = ussd.traiter("9", zone_nom="Bafia")
        self.assertTrue(reponse.startswith("CON "))
        self.assertIn("inconnue", reponse.lower())
        self.assertLessEqual(len(reponse), 182)

    def test_reponse_toujours_bornee(self):
        risque = {**RISQUE, "niveau": "é" * 200, "confiance": "très très longue"}
        for saisie in ["", "1", "2", "3", "4", "99"]:
            with self.subTest(saisie=saisie):
                reponse = ussd.traiter(
                    saisie,
                    zone_nom="Bafia-" + "x" * 80,
                    risque=risque,
                    pluie_30j=1234.5,
                    fenetre_semis={"debut": "2099-12-31", "fin": "2099-12-31"},
                )
                self.assertLessEqual(len(reponse), 182)


class UssdApiTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        Zone.objects.all().delete()
        cls.zone = Zone.objects.create(
            nom="Bafia", slug="bafia", latitude=4.75, longitude=11.23, actif=True
        )
        base = date(2026, 10, 1)
        for i in range(40):
            DailyWeather.objects.create(
                zone=cls.zone,
                date=base + timedelta(days=i),
                precip_mm=2.0,
                tmax_c=30.0,
                tmin_c=21.0,
                source="NASA POWER",
            )

    @patch("apps.sms.views_ussd.evaluer_risque", return_value=RISQUE)
    def test_simuler_menu(self, _):
        reponse = self.client.post(
            "/api/sms/ussd/simuler/",
            data=json.dumps({"text": ""}),
            content_type="application/json",
        )
        self.assertEqual(reponse.status_code, 200)
        corps = reponse.json()
        self.assertTrue(corps["reponse"].startswith("CON "))
        self.assertLessEqual(corps["longueur"], 182)
        self.assertEqual(corps["longueur_max"], 182)
        self.assertTrue(corps["simulation"])
        self.assertEqual(corps["zone"]["slug"], "bafia")

    @patch("apps.sms.views_ussd.evaluer_risque", return_value=RISQUE)
    def test_simuler_risque(self, _):
        reponse = self.client.post(
            "/api/sms/ussd/simuler/",
            data=json.dumps({"text": "1"}),
            content_type="application/json",
        )
        self.assertEqual(reponse.status_code, 200)
        corps = reponse.json()
        self.assertIn("ÉLEVÉ", corps["reponse"])
        self.assertLessEqual(corps["longueur"], 182)

    @patch("apps.sms.views_ussd.evaluer_risque", return_value=RISQUE)
    def test_webhook_text_plain(self, _):
        reponse = self.client.post(
            "/api/sms/ussd/webhook/",
            data={"text": "2", "sessionId": "x", "serviceCode": "*384#", "phoneNumber": "+237677123456"},
        )
        self.assertEqual(reponse.status_code, 200)
        self.assertIn("text/plain", reponse["Content-Type"])
        contenu = reponse.content.decode("utf-8")
        self.assertTrue(contenu.startswith("CON "))
        self.assertIn("mm", contenu)
        self.assertLessEqual(len(contenu), 182)

    @patch("apps.sms.views_ussd.evaluer_risque", return_value=RISQUE)
    def test_webhook_quitter(self, _):
        reponse = self.client.post("/api/sms/ussd/webhook/", data={"text": "4"})
        self.assertEqual(reponse.status_code, 200)
        contenu = reponse.content.decode("utf-8")
        self.assertTrue(contenu.startswith("END "))
        self.assertLessEqual(len(contenu), 182)
