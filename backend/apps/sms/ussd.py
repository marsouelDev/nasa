"""Moteur USSD simulé (phase 5).

Menu court compatible à un client USSD type Africa's Talking : les entrées
sont des chiffres (`*384*1#` → saisie `1`) et chaque réponse est bornée à 182
caractères (limite usuelle d'un SMS USSD court).
"""

from __future__ import annotations

LONGUEUR_MAX_USSD = 182

ACTION_CON = "CON"
ACTION_END = "END"


def _digits(texte: str | None) -> str:
    """Extrait les chiffres d'une saisie USSD brute (`*384*1#` → `1`)."""
    nettoye = str(texte or "").replace("*", "").split("#", 1)[0].strip()
    return nettoye.replace(" ", "")


def _borner(texte: str) -> str:
    """Borne la réponse à 182 caractères, toujours avec l'action USSD."""
    if len(texte) > LONGUEUR_MAX_USSD:
        texte = texte[: LONGUEUR_MAX_USSD - 3] + "..."
    return texte


def menu(zone_nom: str = "Bafia") -> str:
    """Menu principal, affiché tant que l'utilisateur n'a pas répondu."""
    return _borner(
        f"{ACTION_CON} AgroSentry {zone_nom} - 1: risque 2: pluie 30j 3: semis 4: quitter"
    )


def reponse_risque(zone_nom: str, risque: dict | None) -> str:
    """Réponse USSD sur le risque de sécheresse, avec confiance et validation."""
    zone = zone_nom or "Bafia"
    if not (risque or {}).get("disponible"):
        reponse = (
            f"{ACTION_CON} {zone} : donnees meteo indisponibles. "
            "A valider avec un agronome."
        )
    else:
        niveau = str(risque.get("niveau") or "inconnu").lower()
        confiance = str(risque.get("confiance") or "faible").lower()
        reponse = (
            f"{ACTION_CON} {zone} : risque de secheresse {niveau.upper()}, "
            f"confiance {confiance}. A valider avec un agronome."
        )
    return _borner(reponse)


def reponse_pluie(zone_nom: str, pluie_30j: float | None) -> str:
    """Réponse USSD sur les pluies des 30 derniers jours."""
    zone = zone_nom or "Bafia"
    if pluie_30j is None:
        reponse = f"{ACTION_CON} {zone} : pluie 30j indisponible."
    elif pluie_30j <= 0:
        reponse = f"{ACTION_CON} {zone} : aucune pluie enregistree sur 30j."
    else:
        reponse = f"{ACTION_CON} {zone} : pluie des 30 derniers jours {pluie_30j:g} mm."
    return _borner(reponse)


def reponse_semis(zone_nom: str, fenetre: dict | None) -> str:
    """Réponse USSD sur le calendrier de semis recommandé."""
    zone = zone_nom or "Bafia"
    if not fenetre:
        reponse = f"{ACTION_CON} Semis {zone} : fenetre indisponible. A valider avec un agronome."
    else:
        debut = fenetre.get("debut")
        fin = fenetre.get("fin")
        if debut and fin:
            reponse = (
                f"{ACTION_CON} Semis {zone} : fenetre recommandee du {debut} au {fin}. "
                "A valider avec un agronome."
            )
        else:
            reponse = f"{ACTION_CON} Semis {zone} : fenetre indisponible. A valider avec un agronome."
    return _borner(reponse)


def traiter(
    texte: str | None,
    *,
    zone_nom: str = "Bafia",
    risque: dict | None = None,
    fenetre_semis: dict | None = None,
    pluie_30j: float | None = None,
) -> str:
    """Traite une saisie USSD et renvoie la réponse complète (CON/END)."""
    digits = _digits(texte)
    if digits in ("", "0"):
        return menu(zone_nom)
    if digits == "1":
        return reponse_risque(zone_nom, risque)
    if digits == "2":
        return reponse_pluie(zone_nom, pluie_30j)
    if digits == "3":
        return reponse_semis(zone_nom, fenetre_semis)
    if digits == "4":
        return _borner(f"{ACTION_END} AgroSentry. Merci. STOP pour quitter.")
    return _borner(f"{ACTION_CON} Option {digits} inconnue. 1:risque 2:pluie 3:semis 4:quitter")
