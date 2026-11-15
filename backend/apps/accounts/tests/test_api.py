"""Tests des comptes agriculteurs et du consentement (phase 5)."""

from __future__ import annotations

import json

from django.core.exceptions import ValidationError
from django.test import SimpleTestCase, TestCase

from apps.accounts.consentement import TEXTE_CONSENTEMENT, VERSION_CONSENTEMENT
from apps.accounts.models import Agriculteur
from apps.accounts.telephones import masquer_telephone, normaliser_telephone
from apps.data.models import Zone


class TelephonesTests(SimpleTestCase):
    def test_formats_acceptes(self):
        attendus = {
            "677123456": "+237677123456",
            "+237 677 12 34 56": "+237677123456",
            "00237677123456": "+237677123456",
            "237-677-123-456": "+237677123456",
            "(237) 677.12.34.56": "+237677123456",
            "222123456": "+237222123456",
        }
        for saisi, attendu in attendus.items():
            with self.subTest(saisi=saisi):
                self.assertEqual(normaliser_telephone(saisi), attendu)

    def test_numeros_invalides(self):
        for saisi in ("", "12345", "67712345", "377123456", "abcdefghi", None):
            with self.subTest(saisi=saisi):
                with self.assertRaises(ValidationError):
                    normaliser_telephone(saisi)

    def test_masquage(self):
        self.assertEqual(masquer_telephone("+237677123456"), "+2376••••••56")
        self.assertEqual(masquer_telephone(""), "•••")


class InscriptionApiTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        Zone.objects.all().delete()
        cls.bafia = Zone.objects.create(
            nom="Bafia",
            slug="bafia",
            latitude=4.75,
            longitude=11.23,
            actif=True,
        )
        cls.autre = Zone.objects.create(
            nom="Edéa",
            slug="edea",
            latitude=3.8,
            longitude=10.13,
            actif=True,
        )

    def poster(self, chemin: str, donnees: dict):
        return self.client.post(
            chemin, data=json.dumps(donnees), content_type="application/json"
        )

    def test_inscription_sans_consentement_refusee(self):
        reponse = self.poster(
            "/api/inscriptions/",
            {"telephone": "677123456", "consentement": False},
        )
        self.assertEqual(reponse.status_code, 400)
        self.assertIn("consentement", reponse.json())
        self.assertEqual(Agriculteur.objects.count(), 0)

    def test_inscription_avec_consentement_date(self):
        reponse = self.poster(
            "/api/inscriptions/",
            {
                "telephone": "+237 677 12 34 56",
                "zone": "bafia",
                "langue": "fr",
                "nom": "Awa",
                "consentement": True,
            },
        )
        self.assertEqual(reponse.status_code, 201)
        corps = reponse.json()
        self.assertTrue(corps["cree"])
        self.assertNotIn("+237677123456", reponse.content.decode())
        self.assertEqual(corps["agriculteur"]["telephone_masque"], "+2376••••••56")
        self.assertTrue(corps["agriculteur"]["peut_recevoir_sms"])

        agriculteur = Agriculteur.objects.get()
        self.assertEqual(agriculteur.telephone, "+237677123456")
        self.assertEqual(agriculteur.zone, self.bafia)
        self.assertIsNotNone(agriculteur.consentement_le)
        self.assertEqual(agriculteur.consentement_version, VERSION_CONSENTEMENT)
        self.assertEqual(agriculteur.consentement_texte, TEXTE_CONSENTEMENT)
        self.assertIsNone(agriculteur.desinscrit_le)
        self.assertTrue(agriculteur.peut_recevoir_sms)

    def test_reinscription_meme_numero_ne_duplique_pas(self):
        donnees = {"telephone": "677123456", "consentement": True}
        self.assertEqual(self.poster("/api/inscriptions/", donnees).status_code, 201)
        reponse = self.poster(
            "/api/inscriptions/",
            {**donnees, "zone": "edea", "langue": "en", "nom": "Awa"},
        )
        self.assertEqual(reponse.status_code, 200)
        self.assertFalse(reponse.json()["cree"])
        self.assertEqual(Agriculteur.objects.count(), 1)
        agriculteur = Agriculteur.objects.get()
        self.assertEqual(agriculteur.zone, self.autre)
        self.assertEqual(agriculteur.langue, "en")
        self.assertEqual(agriculteur.nom, "Awa")

    def test_numero_invalide_refuse(self):
        reponse = self.poster(
            "/api/inscriptions/", {"telephone": "12345", "consentement": True}
        )
        self.assertEqual(reponse.status_code, 400)
        self.assertIn("telephone", reponse.json())
        self.assertEqual(Agriculteur.objects.count(), 0)

    def test_zone_inconnue_refusee(self):
        reponse = self.poster(
            "/api/inscriptions/",
            {"telephone": "677123456", "zone": "inconnue", "consentement": True},
        )
        self.assertEqual(reponse.status_code, 400)
        self.assertIn("zone", reponse.json())

    def test_desinscription_stop(self):
        donnees = {"telephone": "677123456", "consentement": True}
        self.poster("/api/inscriptions/", donnees)

        reponse = self.poster("/api/desinscription/", {"telephone": "677123456"})
        self.assertEqual(reponse.status_code, 200)
        corps = reponse.json()
        self.assertTrue(corps["desinscrit"])
        self.assertFalse(corps["deja_desinscrit"])
        self.assertFalse(corps["consentement"])

        agriculteur = Agriculteur.objects.get()
        self.assertFalse(agriculteur.consentement)
        self.assertIsNotNone(agriculteur.desinscrit_le)
        self.assertFalse(agriculteur.peut_recevoir_sms)

        seconde = self.poster("/api/desinscription/", {"telephone": "677123456"})
        self.assertEqual(seconde.status_code, 200)
        self.assertTrue(seconde.json()["deja_desinscrit"])

    def test_desinscription_numero_inconnu(self):
        reponse = self.poster("/api/desinscription/", {"telephone": "699999999"})
        self.assertEqual(reponse.status_code, 200)
        corps = reponse.json()
        self.assertFalse(corps["connu"])
        self.assertFalse(corps["desinscrit"])
        self.assertEqual(Agriculteur.objects.count(), 0)

    def test_reinscription_apres_stop(self):
        donnees = {"telephone": "677123456", "consentement": True}
        self.poster("/api/inscriptions/", donnees)
        self.poster("/api/desinscription/", {"telephone": "677123456"})
        reponse = self.poster("/api/inscriptions/", donnees)
        self.assertEqual(reponse.status_code, 200)
        agriculteur = Agriculteur.objects.get()
        self.assertTrue(agriculteur.consentement)
        self.assertIsNone(agriculteur.desinscrit_le)
        self.assertTrue(agriculteur.peut_recevoir_sms)

    def test_statut_inscription(self):
        self.poster(
            "/api/inscriptions/", {"telephone": "677123456", "consentement": True}
        )
        reponse = self.client.get("/api/inscriptions/statut/", {"telephone": "677123456"})
        self.assertEqual(reponse.status_code, 200)
        corps = reponse.json()
        self.assertTrue(corps["connu"])
        self.assertTrue(corps["agriculteur"]["peut_recevoir_sms"])

        inconnu = self.client.get(
            "/api/inscriptions/statut/", {"telephone": "699999999"}
        )
        self.assertEqual(inconnu.status_code, 200)
        self.assertFalse(inconnu.json()["connu"])

        invalide = self.client.get("/api/inscriptions/statut/", {"telephone": "abc"})
        self.assertEqual(invalide.status_code, 400)

    def test_resume_inscriptions(self):
        donnees = {"telephone": "677123456", "consentement": True}
        self.poster("/api/inscriptions/", donnees)
        self.poster("/api/inscriptions/", {**donnees, "telephone": "699999999"})
        self.poster("/api/desinscription/", {"telephone": "699999999"})

        reponse = self.client.get("/api/inscriptions/")
        self.assertEqual(reponse.status_code, 200)
        corps = reponse.json()
        self.assertEqual(corps["nombre_agriculteurs"], 2)
        self.assertEqual(corps["nombre_consentants"], 1)
        self.assertEqual(corps["version_consentement"], VERSION_CONSENTEMENT)
        self.assertEqual(corps["texte_consentement"], TEXTE_CONSENTEMENT)
