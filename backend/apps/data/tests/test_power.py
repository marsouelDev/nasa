"""Tests du client NASA POWER (aucun appel réseau)."""

from datetime import date
from types import SimpleNamespace
from unittest.mock import Mock

import requests
from django.test import SimpleTestCase

from apps.data.services import power

from .aides import FakeResponse, FakeSession, power_payload


class ParsePayloadTests(SimpleTestCase):
    def test_sentinelle_999_devient_none(self):
        charge = {
            "properties": {
                "parameter": {
                    "PRECTOTCORR": {"20250101": -999, "20250102": 5.2},
                    "T2M_MAX": {"20250101": -999, "20250102": 31.0},
                    "T2M_MIN": {"20250101": -999, "20250102": 21.0},
                }
            }
        }
        donnees = power.parse_payload(charge)
        self.assertEqual(donnees[date(2025, 1, 1)], {"precip_mm": None, "tmax_c": None, "tmin_c": None})
        self.assertEqual(
            donnees[date(2025, 1, 2)], {"precip_mm": 5.2, "tmax_c": 31.0, "tmin_c": 21.0}
        )

    def test_parametre_manquant_leve_une_erreur(self):
        with self.assertRaises(power.PowerError):
            power.parse_payload({"properties": {"parameter": {"PRECTOTCORR": {}}}})

    def test_reponse_inattendue_leve_une_erreur(self):
        with self.assertRaises(power.PowerError):
            power.parse_payload({"erreur": "quota dépassé"})


class FetchIntervalTests(SimpleTestCase):
    def setUp(self):
        self.zone = SimpleNamespace(latitude=4.75, longitude=11.23)
        self.debut = date(2025, 1, 1)
        self.fin = date(2025, 1, 10)

    def test_parametres_envoyes_a_power(self):
        session = FakeSession([FakeResponse(power_payload(self.debut, 10, pluie=3.0))])
        donnees = power.fetch_interval(
            self.zone, self.debut, self.fin, session=session, max_retries=1
        )
        self.assertEqual(len(donnees), 10)
        params = session.appels[0]["params"]
        self.assertEqual(params["parameters"], "PRECTOTCORR,T2M_MAX,T2M_MIN")
        self.assertEqual(params["community"], "AG")
        self.assertEqual(params["start"], "20250101")
        self.assertEqual(params["end"], "20250110")
        self.assertEqual(params["latitude"], "4.7500")
        self.assertEqual(params["format"], "JSON")

    def test_reessai_puis_succes(self):
        session = FakeSession(
            [
                requests.ConnectionError("réseau indisponible"),
                FakeResponse(power_payload(self.debut, 10)),
            ]
        )
        pause = Mock()
        donnees = power.fetch_interval(
            self.zone, self.debut, self.fin, session=session, max_retries=3, sleep=pause
        )
        self.assertEqual(len(donnees), 10)
        self.assertEqual(len(session.appels), 2)
        pause.assert_called_once()

    def test_echec_apres_toutes_les_tentatives(self):
        session = FakeSession(
            [requests.ConnectionError("panne") for _ in range(3)]
        )
        with self.assertRaises(power.PowerError):
            power.fetch_interval(
                self.zone,
                self.debut,
                self.fin,
                session=session,
                max_retries=3,
                sleep=Mock(),
            )
        self.assertEqual(len(session.appels), 3)

    def test_erreur_http_est_reessayee(self):
        session = FakeSession(
            [
                FakeResponse({}, status_code=503),
                FakeResponse(power_payload(self.debut, 10)),
            ]
        )
        donnees = power.fetch_interval(
            self.zone, self.debut, self.fin, session=session, max_retries=2, sleep=Mock()
        )
        self.assertEqual(len(donnees), 10)


class PeriodesTests(SimpleTestCase):
    def test_periodes_manquantes(self):
        existantes = [date(2025, 1, 2), date(2025, 1, 3), date(2025, 1, 6)]
        periodes = power.periodes_manquantes(date(2025, 1, 1), date(2025, 1, 6), existantes)
        self.assertEqual(
            periodes,
            [(date(2025, 1, 1), date(2025, 1, 1)), (date(2025, 1, 4), date(2025, 1, 5))],
        )

    def test_decoupage_en_lots(self):
        lots = power.decouper_periode(date(2025, 1, 1), date(2025, 12, 31), jours_par_lot=100)
        self.assertEqual(len(lots), 4)
        self.assertEqual(lots[0], (date(2025, 1, 1), date(2025, 4, 10)))
        self.assertEqual(lots[-1][1], date(2025, 12, 31))
