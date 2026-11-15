# AGENTS.md

## Contexte

Dépôt du projet **AgroSentry** (hackathon, Bafia, Cameroun) : aide à la décision
agro-climatique à partir de données NASA POWER. Dépôt git, remote `origin`
(`github.com/marsouelDev/nasa`), branche `main`. Un commit par phase/bloc, pas de push
automatique.

**Sources de référence**
- `AGROSENTRY.md` — cahier des charges d'exécution (6 phases). Fait foi sur la stack.
- `Cahier_des_charges_AgroSentry_Cameroun_v4_3.docx` — vision produit (docx non lisible
  directement ; demander un export texte ou lire via conversion).
- `agrosentry_model.py` — prototype onset + Random Forest (porté en phase 2).
- `agrosentry_carte_gibs.html` — prototype de carte Leaflet (porté en phase 4).
- `nasa_power_edea.py` — ancien script Edéa, réutiliser seulement la logique POWER.

**Stack** : Django 5.2 LTS + Django REST Framework (backend), React + Vite (frontend).
Pas de FastAPI. `download-all-*.py` et le fichier `.h5` NISAR sont hors périmètre : ne pas
les lancer, les modifier ou les committer.

## État des phases

1. **Backend Django + ingestion POWER** — terminée.
2. **Modèle ML** (onset + Random Forest, `train_models`) — terminée.
3. **Moteur de rotations** (S0/S1/S2, fixtures) — terminée.
4. **Frontend React/Vite/PWA + carte MapLibre 3D** (GIBS, `/api/point/`, pages API) — terminée.
5. **SMS/USSD simulés, Celery eager, comptes et consentement** — terminée (démo, aucun envoi réel).
6. **Finition** (perf, bundle, explications, README, limites, critères MVP) — terminée.

Ne jamais annoncer une fonctionnalité sans l'avoir testée.

## Commandes (Windows PowerShell)

### Installation (une fois)

```powershell
# Racine du dépôt
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env

cd backend
..\.venv\Scripts\python.exe manage.py migrate

cd ..\frontend
npm install
```

### Backend (depuis `backend\`)

```powershell
# Données réelles NASA POWER (réseau requis, incrémental)
..\.venv\Scripts\python.exe manage.py ingest_power --zone bafia

# Entraînement du modèle de risque (données en base requises)
..\.venv\Scripts\python.exe manage.py train_models

# Alertes de risque (Celery eager, exécution immédiate, SMS simulés aux consentants)
..\.venv\Scripts\python.exe manage.py envoyer_alertes [--zone bafia]

# Tests — DOIT être lancé depuis backend/, sinon 0 test découvert
..\.venv\Scripts\python.exe manage.py test

# Serveur + doc OpenAPI
..\.venv\Scripts\python.exe manage.py runserver
# http://127.0.0.1:8000/api/  ·  /api/docs/  ·  /api/schema/  ·  /admin/
```

### Frontend (depuis `frontend\`)

```powershell
npm run dev      # http://localhost:5173 (VITE_API_URL, défaut http://127.0.0.1:8000/api)
npm run build    # tsc + vite build (vérifier $LASTEXITCODE)
npm run lint     # eslint (vérifier $LASTEXITCODE)
```

### Notes d'exécution

- `manage.py` recharge `backend/../.env` et force stdout/stderr en UTF-8 (Windows).
  Si les accents restent illisibles : `chcp 65001`.
- Les tests sont hors réseau (HTTP simulé). L'ingestion réelle exige Internet.
- `ingest_power` est incrémental (cache en base). Options : `--force`, `--start AAAA-MM-JJ`,
  `--end AAAA-MM-JJ|auto` (`auto` = J-2), `--csv chemin`, `--no-csv`, `--timeout`.
  Export CSV par défaut : `backend/exports/power_<zone>.csv` (UTF-8 avec BOM, ignoré par git).
- Le modèle ML est mis en cache mémoire après chargement (rechargé si le fichier change).
- Les données de test ne doivent jamais dépendre du réseau.
- Sous PowerShell, vérifier `$LASTEXITCODE` après `npm run build` / `npm run lint` / scripts.

## Architecture

```
backend/
  agrosentry/          settings (env), urls, celery (eager), wsgi/asgi
  apps/data/           Zone, DailyWeather, IngestionLog ; client POWER, onset, risque,
                       agrégations ; commandes ingest_power et creer_zone ; API
  apps/ml/             Random Forest risque (services, cache, train_models)
  apps/rotations/      comparateur S0/S1/S2 (fixtures, scoring)
  apps/accounts/       Agriculteur, consentement daté/versionné, inscriptions/STOP
  apps/sms/            SMS/USSD simulés, journal EnvoiSMS, tâche alertes Celery eager
frontend/
  src/                 React + Vite, carte MapLibre/GIBS, pages Tendances/Rotations/SMS
```

- La zone Bafia est créée par migration de données (`data/0002_zone_bafia`), pas codée en
  dur dans les vues. `DEFAULT_ZONE_SLUG=bafia`.
- Endpoints principaux : `/api/zones/`, `/api/pluie/`, `/api/pluie/tendances/`,
  `/api/risques/`, `/api/calendrier-semis/`, `/api/point/?lat=&lon=`, `/api/rotations/`,
  `/api/inscriptions/`, `/api/desinscription/`, `/api/sms/apercu/`, `/api/sms/simuler/`,
  `/api/sms/journal/`, `/api/sms/alertes/`, `/api/sms/ussd/webhook/`, `/api/sms/ussd/simuler/`.
- Endpoints démo comptes/SMS/USSD ouverts (`AllowAny`) et SMS/USSD simulés ; à protéger
  avant toute exposition réelle. Écritures sensibles par ailleurs via auth DRF (token/session).
- `source` et `confiance` sont obligatoires dans toute réponse de recommandation ; les
  valeurs simulées doivent être étiquetées « démonstration ».

## Pièges vérifiés

- **POWER** : `community=AG`, dates `YYYYMMDD`, sentinelle `-999` → `NULL`.
- **GIBS (phase 4)** : l'archive `MODIS_Terra_NDVI_8Day` commence le **2025-02-12** et les
  dates sont discontinues. Borner le sélecteur de date et prévoir un repli sur le composite
  précédent. `maxzoom` natif : NDVI/TrueColor 9, LST 7.
- **npm** : registre parfois lent sur cette machine. Installer les dépendances front en une
  fois, avec des timeouts longs ; éviter les paquets inutiles.
- **Tests** : `python manage.py test` depuis la racine découvre 0 test. Toujours `cd backend`.
- **Celery** : `CELERY_TASK_ALWAYS_EAGER=True` par défaut (pas de Redis/worker en démo).
- **SMS** : jamais sans consentement enregistré ; simulation par défaut (`SMS_SIMULATION=True`,
  pas de clés). Longueurs : SMS ≤ 160, USSD ≤ 182 caractères.
- Git ignore déjà `.env`, `db.sqlite3`, `backend/exports/`, `*.h5`, modèles `.pkl/.joblib`,
  `node_modules/`, `dist/`.

## Conventions

- Interface, messages, docstrings et commentaires en **français** ; identifiants de code en
  anglais.
- Aucune clé ni mot de passe dans le code : `.env` (non versionné) + `.env.example` à jour.
- Accessibilité : jamais une information par la couleur seule ; unités et dates affichées.
- Toute recommandation porte un niveau de confiance et la mention « à valider avec un
  agronome ». Les explications de risque doivent être lisibles (sans valeurs brutes techniques).
