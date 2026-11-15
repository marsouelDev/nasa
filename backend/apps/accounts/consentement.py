"""Texte et version du consentement recueilli auprès des agriculteurs.

Le texte est figé au moment de l'inscription : si la formulation change, les
consentements déjà enregistrés conservent la version qu'ils ont acceptée.
"""

from __future__ import annotations

TEXTE_CONSENTEMENT = (
    "J'accepte de recevoir des SMS d'alerte agro-climatique d'AgroSentry sur ce "
    "numéro. Données collectées : numéro, zone et langue. Répondez STOP pour ne "
    "plus recevoir de message."
)

VERSION_CONSENTEMENT = "1.0"

LANGUES = ("fr", "en")
