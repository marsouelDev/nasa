"""Normalisation des numéros de téléphone camerounais.

Un seul format est stocké en base : `+237` suivi des 9 chiffres nationaux
(par exemple `+237677123456`). Les formats saisis par les agriculteurs
(espaces, tirets, `00237`, `237`, `6…`) sont acceptés puis convertis.
"""

from __future__ import annotations

import re

from django.core.exceptions import ValidationError

INDICATIF_CAMEROUN = "+237"
MESSAGE_NUMERO_INVALIDE = (
    "Numéro camerounais invalide : attendu 9 chiffres commençant par 2 ou 6 "
    "(exemple : 677123456 ou +237677123456)."
)


def normaliser_telephone(valeur: str) -> str:
    """Retourne le numéro au format `+237XXXXXXXXX`.

    Lève `ValidationError` si le numéro n'est pas un numéro camerounais
    plausible. Aucune vérification d'opérateur n'est faite.
    """
    if valeur is None:
        raise ValidationError(MESSAGE_NUMERO_INVALIDE)

    nettoye = re.sub(r"[\s.\-()/]", "", str(valeur).strip())
    if nettoye.startswith("00"):
        nettoye = "+" + nettoye[2:]
    if nettoye.startswith(INDICATIF_CAMEROUN):
        national = nettoye[len(INDICATIF_CAMEROUN) :]
    elif nettoye.startswith("237"):
        national = nettoye[3:]
    else:
        national = nettoye

    if not re.fullmatch(r"[26]\d{8}", national):
        raise ValidationError(MESSAGE_NUMERO_INVALIDE)
    return f"{INDICATIF_CAMEROUN}{national}"


def masquer_telephone(telephone: str) -> str:
    """Masque un numéro normalisé : `+2376•••••78`.

    Les réponses publiques de démonstration ne doivent jamais renvoyer un
    numéro complet.
    """
    if not telephone or len(telephone) < 6:
        return "•••"
    return f"{telephone[:5]}{'•' * (len(telephone) - 7)}{telephone[-2:]}"
