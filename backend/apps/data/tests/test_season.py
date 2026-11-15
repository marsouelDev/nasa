"""Tests de la règle de début de saison des pluies."""

from datetime import date, timedelta

from django.test import SimpleTestCase

from apps.data.services import season


def serie_annee(annee: int, pluies_par_jour: dict[date, float]) -> list[tuple[date, float]]:
    debut = date(annee, 1, 1)
    fin = date(annee, 12, 31)
    serie = []
    jour = debut
    while jour <= fin:
        serie.append((jour, pluies_par_jour.get(jour, 0.0)))
        jour += timedelta(days=1)
    return serie


class OnsetTests(SimpleTestCase):
    def test_premier_jour_avec_40_mm_sur_10_jours(self):
        pluies = {date(2016, 3, jour): 5.0 for jour in range(1, 11)}
        onsets = season.onset_dates(serie_annee(2016, pluies))
        # Cumul de 40 mm atteint le 8 mars (1er au 8 mars).
        self.assertEqual(onsets[2016], date(2016, 3, 8))

    def test_pluie_de_janvier_ne_declenche_pas_la_saison(self):
        pluies = {date(2016, 1, jour): 20.0 for jour in range(1, 20)}
        onsets = season.onset_dates(serie_annee(2016, pluies))
        self.assertNotIn(2016, onsets)

    def test_valeurs_manquantes_bloquent_la_detection(self):
        serie = serie_annee(2016, {date(2016, 3, jour): 5.0 for jour in range(1, 11)})
        serie = [
            (jour, None) if date(2016, 3, 4) <= jour <= date(2016, 3, 6) else (jour, pluie)
            for jour, pluie in serie
        ]
        onsets = season.onset_dates(serie)
        # La fenêtre est incomplète jusqu'au 10 mars ; le cumul suivant (11-20 mars)
        # retombe à 40 mm le 20 mars (pluie nulle ensuite, donc pas de détection).
        self.assertNotIn(2016, onsets)


class StatistiquesTests(SimpleTestCase):
    def test_statistiques_et_confiance(self):
        onsets = {annee: date(annee, 3, 10) for annee in range(2016, 2026)}
        stats = season.onset_statistics(onsets)
        self.assertTrue(stats["disponible"])
        self.assertEqual(stats["annees"], 10)
        self.assertEqual(stats["mediane"], "03-10")
        self.assertEqual(stats["confiance"], "élevée")

    def test_serie_courte_donne_confiance_faible(self):
        stats = season.onset_statistics({2016: date(2016, 3, 10)})
        self.assertEqual(stats["confiance"], "faible")

    def test_aucune_donnee(self):
        stats = season.onset_statistics({})
        self.assertFalse(stats["disponible"])
        self.assertIsNone(season.fenetre_pour_annee(stats, 2027))

    def test_fenetre_plus_ou_moins_cinq_jours(self):
        onsets = {annee: date(annee, 3, 10) for annee in range(2016, 2026)}
        stats = season.onset_statistics(onsets)
        fenetre = season.fenetre_pour_annee(stats, 2027)
        self.assertEqual(fenetre, {"debut": "2027-03-05", "fin": "2027-03-15"})
