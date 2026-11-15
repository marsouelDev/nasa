"""Tests des endpoints de l'API data."""

from datetime import date, timedelta

from django.test import TestCase

from apps.data.models import DailyWeather, Zone


class ApiTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        # La zone Bafia est créée par migration ; on la retire pour isoler les tests.
        Zone.objects.filter(slug="bafia").delete()
        cls.zone = Zone.objects.create(
            nom="Ville test",
            slug="testville",
            latitude=4.75,
            longitude=11.23,
        )
        cls.zone_vide = Zone.objects.create(
            nom="Zone vide",
            slug="vide",
            latitude=5.0,
            longitude=12.0,
        )

        lignes = []
        for annee in (2016, 2017, 2018):
            jour = date(annee, 1, 1)
            while jour.year == annee:
                pluie = 5.0 if (jour.month == 3 and jour.day <= 10) else 0.0
                lignes.append(
                    DailyWeather(
                        zone=cls.zone,
                        date=jour,
                        precip_mm=pluie,
                        tmax_c=30.0,
                        tmin_c=20.0,
                        source="NASA POWER",
                    )
                )
                jour += timedelta(days=1)
        DailyWeather.objects.bulk_create(lignes, batch_size=500)

    def get(self, url, **params):
        return self.client.get(url, data=params)

    def test_index_api(self):
        reponse = self.client.get("/api/")
        self.assertEqual(reponse.status_code, 200)
        self.assertIn("endpoints", reponse.json())
        self.assertIn("/api/docs/", reponse.json()["documentation"])
        self.assertIn("/api/schema/", reponse.json()["schema"])

    def test_liste_et_detail_des_zones(self):
        reponse = self.client.get("/api/zones/")
        self.assertEqual(reponse.status_code, 200)
        self.assertEqual([zone["slug"] for zone in reponse.json()], ["testville", "vide"])

        detail = self.client.get("/api/zones/testville/")
        self.assertEqual(detail.status_code, 200)
        self.assertEqual(detail.json()["nom"], "Ville test")

    def test_pluie_annee_complete(self):
        reponse = self.get(
            "/api/pluie/", zone="testville", debut="2018-01-01", fin="2018-12-31"
        )
        self.assertEqual(reponse.status_code, 200)
        donnees = reponse.json()
        self.assertEqual(donnees["nb_jours"], 365)
        self.assertEqual(len(donnees["serie"]), 365)
        self.assertEqual(donnees["derniere_donnee"], "2018-12-31")
        self.assertIn("NASA POWER", donnees["source"])
        self.assertEqual(donnees["debut_saison"]["statistiques"]["annees"], 3)
        self.assertEqual(len(donnees["resume_mensuel"]), 12)

    def test_pluie_fenetre_par_defaut(self):
        reponse = self.get("/api/pluie/", zone="testville")
        self.assertEqual(reponse.status_code, 200)
        self.assertEqual(reponse.json()["nb_jours"], 366)

    def test_pluie_zone_sans_donnees(self):
        reponse = self.get("/api/pluie/", zone="vide")
        self.assertEqual(reponse.status_code, 200)
        self.assertFalse(reponse.json()["disponible"])

    def test_pluie_erreurs_de_parametres(self):
        self.assertEqual(
            self.get("/api/pluie/", zone="testville", debut="hier").status_code, 400
        )
        self.assertEqual(
            self.get(
                "/api/pluie/", zone="testville", debut="2018-12-31", fin="2018-01-01"
            ).status_code,
            400,
        )
        self.assertEqual(self.get("/api/pluie/", zone="testville", fin="2018-01-01", debut="1990-01-01").status_code, 400)

    def test_zone_inconnue(self):
        self.assertEqual(self.get("/api/pluie/", zone="absente").status_code, 404)

    def test_tendances(self):
        reponse = self.get(
            "/api/pluie/tendances/", zone="testville", annee=2018, annees_reference=2
        )
        self.assertEqual(reponse.status_code, 200)
        tendance = reponse.json()["tendance"]
        self.assertEqual(tendance["annee_courante"], 2018)
        self.assertEqual(tendance["annees_reference"], [2016, 2017])
        self.assertEqual(len(tendance["labels"]), 12)
        self.assertEqual(tendance["pluie_courante_mm"][2], 50.0)
        self.assertEqual(tendance["pluie_moyenne_reference_mm"][2], 50.0)

    def test_risques(self):
        reponse = self.get("/api/risques/", zone="testville", culture="maïs")
        self.assertEqual(reponse.status_code, 200)
        donnees = reponse.json()
        self.assertEqual(donnees["niveau"], "élevé")
        self.assertEqual(donnees["confiance"], "élevée")
        self.assertTrue(donnees["a_valider_par_agronome"])
        self.assertFalse(donnees["culture_prise_en_compte"])

    def test_risques_zone_sans_donnees(self):
        reponse = self.get("/api/risques/", zone="vide")
        self.assertEqual(reponse.status_code, 200)
        self.assertFalse(reponse.json()["disponible"])

    def test_calendrier_semis(self):
        reponse = self.get("/api/calendrier-semis/", zone="testville", annee=2019)
        self.assertEqual(reponse.status_code, 200)
        donnees = reponse.json()
        self.assertTrue(donnees["disponible"])
        self.assertEqual(donnees["fenetre_recommandee"], {"debut": "2019-03-03", "fin": "2019-03-13"})
        self.assertEqual(donnees["annee"], 2019)

    def test_point_le_plus_proche(self):
        reponse = self.get("/api/point/", lat=4.76, lon=11.24)
        self.assertEqual(reponse.status_code, 200)
        donnees = reponse.json()
        self.assertEqual(donnees["zone"]["slug"], "testville")
        self.assertLess(donnees["distance_km"], 5)
        self.assertIn("NASA POWER", donnees["source"])
        self.assertTrue(donnees["meteo"]["disponible"])
        self.assertIn("scenarios", donnees["rotation"])

    def test_point_parametres_invalides(self):
        self.assertEqual(self.client.get("/api/point/").status_code, 400)
        self.assertEqual(self.get("/api/point/", lat=120, lon=11).status_code, 400)

    def test_schema_openapi(self):
        reponse = self.client.get("/api/schema/")
        self.assertEqual(reponse.status_code, 200)
