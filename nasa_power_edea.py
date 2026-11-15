"""
Récupère les données météo NASA POWER pour Edéa (Cameroun),
les enregistre en CSV et trace un graphique pluie / température.

Installation (une seule fois) :
    pip install requests pandas matplotlib

Lancement :
    python nasa_power_edea.py
"""

import requests
import pandas as pd
import matplotlib.pyplot as plt

# --- Paramètres à modifier si besoin ---------------------------------------
LATITUDE = 3.80      # Edéa
LONGITUDE = 10.13
DATE_DEBUT = "20250101"   # format AAAAMMJJ
DATE_FIN = "20251231"
# ---------------------------------------------------------------------------

URL = "https://power.larc.nasa.gov/api/temporal/daily/point"

PARAMETRES = {
    "PRECTOTCORR": "Pluie (mm/jour)",
    "T2M": "Température moyenne (°C)",
    "T2M_MAX": "Température max (°C)",
    "T2M_MIN": "Température min (°C)",
    "RH2M": "Humidité relative (%)",
    "ALLSKY_SFC_SW_DWN": "Rayonnement solaire (kWh/m²/jour)",
}

params = {
    "parameters": ",".join(PARAMETRES.keys()),
    "community": "AG",
    "longitude": LONGITUDE,
    "latitude": LATITUDE,
    "start": DATE_DEBUT,
    "end": DATE_FIN,
    "format": "JSON",
}

print("Téléchargement des données NASA POWER pour Edéa...")
reponse = requests.get(URL, params=params, timeout=120)
reponse.raise_for_status()
donnees = reponse.json()["properties"]["parameter"]

# Construction du tableau (une colonne par paramètre)
df = pd.DataFrame(donnees)
df.index = pd.to_datetime(df.index, format="%Y%m%d")
df.index.name = "date"

# NASA POWER utilise -999 pour les valeurs manquantes
df = df.replace(-999, pd.NA).astype(float)
df = df.rename(columns=PARAMETRES)

# Sauvegarde CSV
fichier_csv = "nasa_power_edea.csv"
df.to_csv(fichier_csv, encoding="utf-8-sig")
print(f"CSV enregistré : {fichier_csv} ({len(df)} jours)")

# Résumé mensuel
mensuel = pd.DataFrame({
    "Pluie totale (mm)": df["Pluie (mm/jour)"].resample("MS").sum(),
    "Température moyenne (°C)": df["Température moyenne (°C)"].resample("MS").mean(),
})
print("\nRésumé mensuel :")
print(mensuel.round(1).to_string())

# Graphique
fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(11, 8), sharex=True)

ax1.bar(df.index, df["Pluie (mm/jour)"], color="steelblue", width=1.0)
ax1.set_ylabel("Pluie (mm/jour)")
ax1.set_title(f"Edéa ({LATITUDE}°N, {LONGITUDE}°E) - NASA POWER")

ax2.plot(df.index, df["Température max (°C)"], color="tomato", label="Max", linewidth=0.8)
ax2.plot(df.index, df["Température moyenne (°C)"], color="black", label="Moyenne", linewidth=0.8)
ax2.plot(df.index, df["Température min (°C)"], color="royalblue", label="Min", linewidth=0.8)
ax2.set_ylabel("Température (°C)")
ax2.legend()

plt.tight_layout()
fichier_png = "nasa_power_edea.png"
plt.savefig(fichier_png, dpi=150)
print(f"\nGraphique enregistré : {fichier_png}")
plt.show()
