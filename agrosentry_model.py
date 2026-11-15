"""AgroSentry : modèle ML explicable sur données NASA POWER (Bafia).
Installation : pip install requests pandas scikit-learn joblib
Usage        : python agrosentry_model.py
Non testé sur l'API réelle : à lancer d'abord avec une bonne connexion.
"""
import requests, pandas as pd, joblib
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import TimeSeriesSplit, cross_val_score

LAT, LON = 4.75, 11.23
START, END = "20160101", "20251231"

def fetch_power():
    url = "https://power.larc.nasa.gov/api/temporal/daily/point"
    p = {"parameters": "PRECTOTCORR,T2M_MAX,T2M_MIN", "community": "AG",
         "latitude": LAT, "longitude": LON, "start": START, "end": END, "format": "JSON"}
    r = requests.get(url, params=p, timeout=120)
    r.raise_for_status()
    d = pd.DataFrame(r.json()["properties"]["parameter"])
    d.index = pd.to_datetime(d.index, format="%Y%m%d")
    return d.replace(-999, pd.NA).dropna().astype(float).rename(
        columns={"PRECTOTCORR": "rain", "T2M_MAX": "tmax", "T2M_MIN": "tmin"})

def onset_dates(d):
    """Début de saison (règle explicable) : premier jour après le 1er mars
    où le cumul sur 10 jours dépasse 40 mm."""
    out = {}
    roll = d["rain"].rolling(10).sum()
    for y in sorted(set(d.index.year)):
        s = roll[f"{y}-03-01":f"{y}-06-30"]
        hit = s[s >= 40]
        if len(hit): out[y] = hit.index[0].date()
    return out

def build_features(d):
    f = pd.DataFrame(index=d.index)
    f["rain7"], f["rain30"] = d["rain"].rolling(7).sum(), d["rain"].rolling(30).sum()
    f["tmax7"] = d["tmax"].rolling(7).mean()
    f["dry_days14"] = (d["rain"] < 1).rolling(14).sum()
    f["doy"] = d.index.dayofyear
    # Cible : poche de sécheresse dans les 15 prochains jours (>= 10 jours sans pluie)
    nxt = (d["rain"] < 1).astype(int)[::-1].rolling(15).sum()[::-1].shift(-1)
    f["target"] = (nxt >= 10).astype(int)
    return f.dropna()

if __name__ == "__main__":
    data = fetch_power()
    print("Début de saison par année :", onset_dates(data))
    f = build_features(data)
    X, y = f.drop(columns="target"), f["target"]
    rf = RandomForestClassifier(n_estimators=200, max_depth=8, min_samples_leaf=10,
                                class_weight="balanced", random_state=0)
    print("Précision (validation temporelle) :",
          cross_val_score(rf, X, y, cv=TimeSeriesSplit(5), scoring="balanced_accuracy").round(2))
    rf.fit(X, y)
    print("Importance des variables :", dict(zip(X.columns, rf.feature_importances_.round(2))))
    joblib.dump(rf, "risque_secheresse.pkl")
    data.to_csv("bafia_clean_ml_ready.csv")
