"""Génère les icônes PNG de la PWA AgroSentry (aucune dépendance externe).

Usage (depuis `frontend/`) :
    ..\\.venv\\Scripts\\python.exe scripts/generer_icones.py

Le dessin est volontairement simple : fond vert, feuille claire, soleil jaune.
Les fichiers produits sont versionnés dans `public/icons/`.
"""

from __future__ import annotations

import math
import struct
import zlib
from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent
DOSSIER_SORTIE = RACINE / "public" / "icons"

FOND = (15, 46, 29)
FEUILLE = (232, 245, 233)
NERVURE = (46, 125, 50)
SOLEIL = (255, 193, 7)


def couleur_pixel(u: float, v: float) -> tuple[int, int, int]:
    """Couleur d'un point normalisé (u, v) dans [-1, 1]."""
    # Feuille : ellipse inclinée à 45°.
    angle = math.radians(45)
    a = u * math.cos(angle) + v * math.sin(angle)
    b = -u * math.sin(angle) + v * math.cos(angle)
    if (a / 0.52) ** 2 + (b / 0.26) ** 2 <= 1.0:
        if abs(b) < 0.022 and a < 0.52:
            return NERVURE
        return FEUILLE

    # Soleil en haut à droite.
    if (u - 0.48) ** 2 + (v + 0.48) ** 2 <= 0.14**2:
        return SOLEIL

    return FOND


def ecrire_png(taille: int, chemin: Path) -> None:
    """Écrit un PNG RGBA avec un anticrénelage 2x2."""
    lignes = bytearray()
    echantillons = 2
    for y in range(taille):
        lignes.append(0)  # filtre « None »
        for x in range(taille):
            rouge = vert = bleu = 0
            for dy in range(echantillons):
                for dx in range(echantillons):
                    u = ((x + (dx + 0.5) / echantillons) / taille) * 2 - 1
                    v = ((y + (dy + 0.5) / echantillons) / taille) * 2 - 1
                    r, g, b = couleur_pixel(u, v)
                    rouge += r
                    vert += g
                    bleu += b
            total = echantillons * echantillons
            lignes.extend((rouge // total, vert // total, bleu // total, 255))

    def bloc(nom: bytes, donnees: bytes) -> bytes:
        return (
            struct.pack(">I", len(donnees))
            + nom
            + donnees
            + struct.pack(">I", zlib.crc32(nom + donnees) & 0xFFFFFFFF)
        )

    entete = struct.pack(">IIBBBBB", taille, taille, 8, 6, 0, 0, 0)
    png = (
        b"\x89PNG\r\n\x1a\n"
        + bloc(b"IHDR", entete)
        + bloc(b"IDAT", zlib.compress(bytes(lignes), 9))
        + bloc(b"IEND", b"")
    )
    chemin.write_bytes(png)
    print(f"Écrit : {chemin} ({taille}x{taille}, {len(png)} octets)")


def main() -> None:
    DOSSIER_SORTIE.mkdir(parents=True, exist_ok=True)
    for taille in (192, 512):
        ecrire_png(taille, DOSSIER_SORTIE / f"icon-{taille}.png")


if __name__ == "__main__":
    main()
