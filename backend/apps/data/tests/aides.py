"""Outils de test : payloads POWER simulés et faux client HTTP."""

from __future__ import annotations

from datetime import date, timedelta

import requests

from apps.data.services import power


def power_payload(
    debut: date,
    jours: int,
    *,
    pluie: float = 0.0,
    tmax: float = 30.0,
    tmin: float = 20.0,
) -> dict:
    precipitations: dict[str, float] = {}
    maxima: dict[str, float] = {}
    minima: dict[str, float] = {}
    for decalage in range(jours):
        jour = debut + timedelta(days=decalage)
        cle = jour.strftime("%Y%m%d")
        precipitations[cle] = pluie
        maxima[cle] = tmax
        minima[cle] = tmin
    return {
        "properties": {
            "parameter": {
                "PRECTOTCORR": precipitations,
                "T2M_MAX": maxima,
                "T2M_MIN": minima,
            }
        }
    }


class FakeResponse:
    def __init__(self, payload: dict, status_code: int = 200):
        self.payload = payload
        self.status_code = status_code

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(f"HTTP {self.status_code}")

    def json(self):
        return self.payload


class FakeSession:
    """Faux client HTTP : rejoue une séquence de réponses ou d'exceptions."""

    def __init__(self, reponses: list):
        self.reponses = list(reponses)
        self.appels: list[dict] = []

    def get(self, url, params=None, timeout=None):
        self.appels.append({"url": url, "params": params, "timeout": timeout})
        if not self.reponses:
            raise AssertionError("Aucune réponse simulée restante.")
        element = self.reponses.pop(0)
        if isinstance(element, Exception):
            raise element
        return element


def donnees_power(debut: date, jours: int, **options) -> dict:
    """Payload POWER déjà normalisé, tel que renvoyé par fetch_interval."""
    return power.parse_payload(power_payload(debut, jours, **options))
