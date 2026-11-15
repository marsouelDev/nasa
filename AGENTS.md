# AGENTS.md

## Contexte

Dépôt du projet **AgroSentry** (hackathon, Bafia, Cameroun) : aide à la décision
agro-climatique à partir de données NASA POWER. Dépôt git, remote `origin`
(`github.com/marsouelDev/nasa`), branche `main`. Un commit par phase, pas de push
automatique.

**Sources à lire avant de coder**
- `AGROSENTRY.md` — cahier des charges d'exécution (6 phases). Fait foi sur la stack.
- `Cahier_des_charges_AgroSentry_Cameroun_v4_3.docx` — vision produit (docx non lisible
  directement ; demander un export texte ou lire via conversion).
- `agrosentry_model.py` — prototype onset + Random Forest (à porter en phase 2).
- `agrosentry_carte_gibs.html` — prototype de carte Leaflet (à porter en phase 4).
- `nasa_power_edea.py` — ancien script Edéa, réutiliser seulement la logique POWER.

**Stack imposée** : Django 5.2 LTS + Django REST Framework (backend), React + Vite (frontend).
Pas de FastAPI. `download-all-*.py` et le fichier `.h5` NISAR sont hors périmètre : ne pas
les lancer, les modifier ou les committer.

## État des phases

1. **Backend Django + ingestion POWER — terminée** (en attente de validation).
2. Modèle ML (onset + Random Forest) — à faire.
3. Moteur de rotations — à faire.
4. Frontend React/Vite/PWA + carte MapLibre 3D — à faire.
5. SMS/USSD simulés — à faire.
6. Finition (README, lint, limites, AGENTS.md) — à faire.

S'arrêter et attendre validation à la fin de chaque phase. Ne jamais annoncer une
fonctionnalité sans l'avoir testée.

## Commandes (Windows PowerShell)

```powershell
# Installation (une fois)
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt

# Base + données réelles (réseau requis, ~15 s)
cd backend
python manage.py migrate
python manage.py ingest_power --zone bafia

# Tests — DOIT être lancé depuis backend/, sinon 0 test découvert
python manage.py test

# Serveur + doc OpenAPI
python manage.py runserver
# http://127.0.0.1:8000/api/  ·  /api/docs/  ·  /api/schema/  ·  /admin/
```

- `manage.py` recharge `backend/../.env` et force stdout/stderr en UTF-8 (Windows).
  Si les accents restent illisibles : `chcp 65001`.
- Les tests sont hors réseau (HTTP simulé). L'ingestion réelle exige Internet.
- `ingest_power` est incrémental : il ne demande que les dates absentes (cache en base).
  Options : `--force`, `--start AAAA-MM-JJ`, `--end AAAA-MM-JJ|auto` (`auto` = J-2),
  `--csv chemin`, `--no-csv`, `--timeout`.
- Export CSV par défaut : `backend/exports/power_<zone>.csv` (UTF-8 avec BOM, ignoré par git).
- Les données de test ne doivent jamais dépendre du réseau.

## Architecture

```
backend/
  agrosentry/          settings (env), urls, wsgi/asgi
  apps/data/           Zone, DailyWeather, IngestionLog ; client POWER, onset, risque,
                       agrégations ; commandes ingest_power et creer_zone ; API
  apps/ml/             phase 2
  apps/rotations/      phase 3
  apps/sms/            phase 5
  apps/accounts/       phase 5 (coopératives, membres, consentement)
```

- La zone Bafia est créée par migration de données (`data/0002_zone_bafia`), pas codée en
  dur dans les vues. `DEFAULT_ZONE_SLUG=bafia` dans les settings/.env.
- Endpoints actuels : `/api/zones/`, `/api/pluie/`, `/api/pluie/tendances/`,
  `/api/risques/`, `/api/calendrier-semis/`, `/api/point/?lat=&lon=`.
- Écritures : authentification par jeton (`rest_framework.authtoken`), lecture publique.
- `source` et `confiance` sont obligatoires dans toute réponse de recommandation ;
  les valeurs simulées doivent être étiquetées « démonstration ».

## Pièges vérifiés

- **POWER** : `community=AG`, dates `YYYYMMDD`, sentinelle `-999` → `NULL`. 2016-01-01 →
  J-2 = 3 969 jours, aucun `-999` sur Bafia au 15/11/2026 ; le jour J-1 peut manquer.
- **GiBS (phase 4)** : l'archive `MODIS_Terra_NDVI_8Day` commence le **2025-02-12** (un
  tile au 2025-01-01 renvoie 404) et les dates sont discontinues. Borner le sélecteur de
  date et prévoir un repli sur le composite précédent. `maxzoom` natif : NDVI/TrueColor 9,
  LST 7.
- **npm** : le registre répond à ~40 Ko/s sur cette machine. Installer les dépendances
  front en une fois, avec des timeouts longs ; éviter les paquets inutiles.
- **Tests** : `python manage.py test` depuis la racine découvre 0 test. Toujours `cd backend`.
- Git ignore déjà `.env`, `db.sqlite3`, `backend/exports/`, `*.h5`, modèles `.pkl/.joblib`,
  `node_modules/`, `dist/`.

## Conventions

- Interface, messages, docstrings et commentaires en **français** ; identifiants de code en
  anglais.
- Aucune clé ni mot de passe dans le code : `.env` (non versionné) + `.env.example` à jour.
- Accessibilité : jamais une information par la couleur seule ; unités et dates affichées.
- Toute recommandation porte un niveau de confiance et la mention « à valider avec un
  agronome ».
