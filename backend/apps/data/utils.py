"""Petits utilitaires partagés par les vues data."""

from __future__ import annotations

from datetime import date, datetime

from rest_framework.exceptions import ValidationError


def parse_date_param(valeur: str | None, nom: str) -> date | None:
    """Lit une date ISO (AAAA-MM-JJ) depuis un paramètre de requête."""
    if valeur in (None, ""):
        return None
    try:
        return datetime.strptime(valeur, "%Y-%m-%d").date()
    except ValueError as exc:
        raise ValidationError(
            {nom: f"Date invalide « {valeur} » : format attendu AAAA-MM-JJ."}
        ) from exc


def parse_int_param(valeur: str | None, nom: str, defaut: int, minimum: int, maximum: int) -> int:
    if valeur in (None, ""):
        return defaut
    try:
        nombre = int(valeur)
    except (TypeError, ValueError) as exc:
        raise ValidationError({nom: f"Valeur entière attendue, reçu « {valeur} »."}) from exc
    if not minimum <= nombre <= maximum:
        raise ValidationError({nom: f"Valeur attendue entre {minimum} et {maximum}."})
    return nombre


def parse_float_param(valeur: str | None, nom: str, minimum: float, maximum: float) -> float:
    if valeur in (None, ""):
        raise ValidationError({nom: "Paramètre obligatoire."})
    try:
        nombre = float(valeur)
    except (TypeError, ValueError) as exc:
        raise ValidationError({nom: f"Nombre attendu, reçu « {valeur} »."}) from exc
    if not minimum <= nombre <= maximum:
        raise ValidationError({nom: f"Valeur attendue entre {minimum} et {maximum}."})
    return nombre
