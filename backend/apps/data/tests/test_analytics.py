"""Tests des agrégations (résumés mensuels, tendances, distances)."""

from datetime import date, timedelta

from django.test import SimpleTestCase

from apps.data.services import analytics


class ResumeMensuelTests(SimpleTestCase):
    def test_cumul_et_moyenne(self):
        lignes = [
            {"date": date(2026, 1, 1), "precip_mm": 10.0, "tmax_c": 30.0},
            {"date": date(2026, 1, 2), "precip_mm": 5.0, "tmax_c": 32.0},
            {"date": date(2026, 2, 1), "precip_mm": 0.0, "tmax_c": 31.0},
        ]
        resume = analytics.monthly_summary(lignes)
        self.assertEqual(len(resume), 2)
        self.assertEqual(resume[0]["mois"], "2026-01")
        self.assertEqual(resume[0]["pluie_mm"], 15.0)
        self.assertEqual(resume[0]["temp_moyenne_c"], 31.0)
        self.assertEqual(resume[0]["jours"], 2)


class TendancesTests(SimpleTestCase):
    def setUp(self):
        serie = []
        for annee in (2016, 2017, 2018):
            for mois in range(1, 13):
                for jour in (1, 15):
                    pluie = 10.0 if mois == 3 else 1.0
                    serie.append((date(annee, mois, jour), pluie, 30.0))
        self.serie = serie

    def test_compare_annee_courante_et_reference(self):
        tendance = analytics.trend_comparison(self.serie, 2018, 2)
        self.assertEqual(tendance["annee_courante"], 2018)
        self.assertEqual(tendance["annees_reference"], [2016, 2017])
        self.assertEqual(len(tendance["labels"]), 12)
        self.assertEqual(tendance["pluie_courante_mm"][2], 20.0)
        self.assertEqual(tendance["pluie_moyenne_reference_mm"][2], 20.0)
        self.assertEqual(tendance["temp_moyenne_reference_c"][2], 30.0)

    def test_mois_sans_donnee_est_null(self):
        serie = [(date(2018, 1, 1), 5.0, 30.0)]
        tendance = analytics.trend_comparison(serie, 2018, 0)
        self.assertEqual(tendance["pluie_courante_mm"][0], 5.0)
        self.assertIsNone(tendance["pluie_courante_mm"][1])


class ResumeRecentTests(SimpleTestCase):
    def test_cumuls_sept_et_trente_jours(self):
        debut = date(2026, 1, 1)
        serie = [
            (debut + timedelta(days=i), 1.0 if i >= 23 else 0.0, 28.0 + i * 0.1)
            for i in range(30)
        ]
        resume = analytics.recent_summary(serie)
        self.assertTrue(resume["disponible"])
        self.assertEqual(resume["pluie_7j_mm"], 7.0)
        self.assertEqual(resume["pluie_30j_mm"], 7.0)
        self.assertEqual(resume["derniere_date"], "2026-01-30")

    def test_serie_vide(self):
        self.assertFalse(analytics.recent_summary([])["disponible"])


class DistanceTests(SimpleTestCase):
    def test_distance_bafia_yaounde(self):
        distance = analytics.haversine_km(4.75, 11.23, 3.848, 11.502)
        self.assertGreater(distance, 100)
        self.assertLess(distance, 130)
