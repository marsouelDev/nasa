# AgroSentry (MVP) â€” Bafia, Cameroun

Prototype dâ€™aide Ã  la dÃ©cision agro-climatique pour la zone de Bafia, basÃ© sur des donnÃ©es NASA POWER (mÃ©tÃ©o quotidienne), un modÃ¨le de risque de poche de sÃ©cheresse, un comparateur de rotations et une console SMS/USSD **simulÃ©e**.

> DÃ©monstration / MVP : les recommandations sont indicatives (donnÃ©es de maille, pas de parcelle) et doivent Ãªtre **validÃ©es avec un agronome**. Aucun SMS rÃ©el nâ€™est envoyÃ© et aucun rÃ©seau mobile nâ€™est contactÃ© sans configuration explicite.

## Pile technique

- **Backend** : Django 5.2 LTS + Django REST Framework, SQLite en dÃ©veloppement
- **Frontend** : React + Vite (TypeScript), carte MapLibre GL, Chart.js
- **DonnÃ©es** : NASA POWER (communautÃ© AG), tuiles NASA GIBS cÃ´tÃ© carte
- **ML** : Random Forest (scikit-learn), artefact `backend/ml/risque_secheresse.joblib`

## PrÃ©requis (Windows)

- Python 3.11+ (testÃ© avec 3.14) et `pip`
- Node.js 18+ et `npm`
- AccÃ¨s Internet pour lâ€™installation des dÃ©pendances, `ingest_power` (API NASA POWER) et les fonds/tuiles de la carte

Toutes les commandes ci-dessous sont donnÃ©es pour **PowerShell** depuis la racine du dÃ©pÃ´t (`D:\Project\nasa` dans les exemples).

## Installation

### 1. Variables dâ€™environnement

```powershell
Copy-Item .env.example .env
# Ã‰diter .env si besoin (SECRET_KEY, hÃ´tes, options SMS/Celery).
# Par dÃ©faut tout reste en mode simulÃ© ; ne pas mettre de clÃ©s rÃ©elles dans le dÃ©pÃ´t.
```

### 2. Backend (Python)

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt

cd backend
..\.venv\Scripts\python.exe manage.py migrate
```

> Si lâ€™environnement virtuel nâ€™est pas activÃ©, utiliser `..\.venv\Scripts\python.exe` depuis `backend\` (recommandÃ© dans ce dÃ©pÃ´t).

### 3. Frontend (Node)

```powershell
cd frontend
npm install
```

## Lancement

### Backend

```powershell
cd backend
..\.venv\Scripts\python.exe manage.py runserver
```

- API : http://127.0.0.1:8000/api/
- Documentation OpenAPI (Swagger) : http://127.0.0.1:8000/api/docs/
- SchÃ©ma : http://127.0.0.1:8000/api/schema/
- Administration : http://127.0.0.1:8000/admin/

### Frontend

```powershell
cd frontend
npm run dev
```

Application : http://localhost:5174 (proxy/requÃªtes vers lâ€™API via `VITE_API_URL`, dÃ©faut `http://127.0.0.1:8000/api`, voir `frontend/.env.example`).

## DonnÃ©es et modÃ¨le

### Ingestion NASA POWER (`ingest_power`)

TÃ©lÃ©charge les donnÃ©es mÃ©tÃ©o quotidiennes rÃ©elles pour une zone et les stocke en base (rÃ©seau requis). Lâ€™ingestion est incrÃ©mentale (ne redemande que les dates absentes).

```powershell
cd backend
..\.venv\Scripts\python.exe manage.py ingest_power --zone bafia
```

Options utiles : `--force`, `--start AAAA-MM-JJ`, `--end AAAA-MM-JJ|auto` (`auto` = Jâˆ’2), `--csv chemin`, `--no-csv`, `--timeout`. Export CSV par dÃ©faut : `backend/exports/power_<zone>.csv`.

### EntraÃ®nement du modÃ¨le (`train_models`)

EntraÃ®ne le Random Forest de risque de sÃ©cheresse sur les donnÃ©es prÃ©sentes en base et sauvegarde lâ€™artefact.

```powershell
cd backend
..\.venv\Scripts\python.exe manage.py train_models
```

Le backend met le modÃ¨le en cache mÃ©moire aprÃ¨s chargement (rechargÃ© si le fichier change), ce qui accÃ©lÃ¨re `/api/point/` et `/api/risques/`.

### Autres commandes

- `python manage.py creer_zone ...` : crÃ©er une zone (la zone Bafia est crÃ©Ã©e par migration)
- `python manage.py envoyer_alertes [--zone bafia]` : dÃ©clenche la tÃ¢che dâ€™alertes (Celery en mode eager par dÃ©faut, exÃ©cution immÃ©diate, SMS simulÃ©s)

## Tests et qualitÃ©

> Les tests backend doivent Ãªtre lancÃ©s **depuis `backend\`** (sinon 0 test dÃ©couvert).

```powershell
cd backend
..\.venv\Scripts\python.exe manage.py test
```

Frontend :

```powershell
cd frontend
npm run lint
npm run build
```

Sous PowerShell, vÃ©rifier le code de sortie avec `$LASTEXITCODE` aprÃ¨s chaque commande (`0` attendu).

## Variables dâ€™environnement principales (`.env`)

Voir `.env.example` pour la liste complÃ¨te. Points importants :

- `DJANGO_SECRET_KEY`, `DJANGO_DEBUG`, `DJANGO_ALLOWED_HOSTS`
- `FRONTEND_URL`, `CORS_ALLOWED_ORIGINS`
- `DB_ENGINE` (`sqlite` par dÃ©faut) et paramÃ¨tres PostgreSQL optionnels
- `POWER_API_URL`, `POWER_TIMEOUT`, `POWER_MAX_RETRIES`
- `AT_USERNAME`, `AT_API_KEY`, `AT_SENDER_ID` : laisser vides en dÃ©mo (mode simulÃ©)
- `SMS_SIMULATION=True`, `SMS_ENVOI_REEL=False` : garde-fous (aucun envoi rÃ©el sans opt-in explicite)
- `CELERY_BROKER_URL=memory://`, `CELERY_TASK_ALWAYS_EAGER=True` : exÃ©cution immÃ©diate sans Redis

Frontend : `VITE_API_URL` (voir `frontend/.env.example`).

## Limites connues

- **SMS/USSD simulÃ©s** : aucun message rÃ©el nâ€™est transmis et aucun rÃ©seau mobile nâ€™est contactÃ©. Les envois sont journalisÃ©s en base ; lâ€™USSD/webhook renvoie des rÃ©ponses texte de dÃ©monstration.
- **Celery en mode eager, sans Redis** : les tÃ¢ches dâ€™alerte sâ€™exÃ©cutent immÃ©diatement (dÃ©mo) ; pas de file, de worker dÃ©diÃ© ni de planification distribuÃ©e.
- **Endpoints de dÃ©monstration ouverts (`AllowAny`)** : inscription, simulation SMS/USSD et dÃ©clenchement dâ€™alertes sont accessibles sans jeton pour la console de dÃ©mo ; Ã  protÃ©ger (authentification/signature) avant toute exposition rÃ©elle.
- **Carte / GIBS** : l’archive NDVI 8 jours commence le 2025-02-12 et les dates sont discontinues ; un repli sur le composite précédent est prévu mais le **composite de repli GIBS n’est pas testé en conditions réelles**. `maxzoom` natif : NDVI/TrueColor 9, LST 7.
- **PWA / hors-ligne** : service worker enregistré en production uniquement ; **service worker non testé hors-ligne** de bout en bout.
- **IcÃ´nes PWA provisoires** : icÃ´nes gÃ©nÃ©rÃ©es pour la dÃ©mo, Ã  remplacer par des visuels dÃ©finitifs.
- **DonnÃ©es et modÃ¨le** : valeurs issues de la maille NASA POWER (~0,5Â°), pas dâ€™une parcelle ; sÃ©ries SMAP/MODIS temporelles non branchÃ©es cÃ´tÃ© backend ; notes/fixtures de rotation Ã  valider avec des agronomes ; prÃ©cision du modÃ¨le Ã  interprÃ©ter avec prudence (cible proche de certaines variables). Tout rÃ©sultat est **Ã  valider avec un agronome**.
- **Bundle** : le chunk initial est < 500 kB, mais les chunks lazy (carte MapLibre, graphiques) restent volumineux.

## CritÃ¨res dâ€™acceptation du MVP

- [x] `ingest_power` remplit la base avec des donnÃ©es rÃ©elles de Bafia (commande opÃ©rationnelle, rÃ©seau requis).
- [x] La carte 3D sâ€™ouvre sur Bafia avec relief, bascule Plan/Satellite et couches NASA GIBS (NDVI, LST, couleur vraie) avec sÃ©lecteur de date et repli prÃ©vu.
- [x] Un clic sur la carte affiche des valeurs issues de lâ€™API (`/api/point/`) avec source, confiance et avertissement agronome.
- [x] Le comparateur affiche 3 rotations (S0/S1/S2) avec rubriques, pondÃ©rations/prioritÃ©s et niveau de confiance (fixtures de dÃ©monstration).
- [x] Le simulateur produit un SMS de 160 caractÃ¨res au plus (aperÃ§u/simulation, journal en base, consentement requis).
- [x] USSD simulÃ© (menu risque/pluie/semis) avec rÃ©ponses â‰¤ 182 caractÃ¨res et alertes Celery eager aux consentants uniquement.
- [x] Tests backend passants et build/lint frontend passants (voir section Tests et qualitÃ©).
- [x] Section « Limites connues » documentée dans le README.
- [ ] `ingest_power` exÃ©cutÃ© sur un environnement cible vierge avec preuve rÃ©seau jointe dans ce dÃ©pÃ´t (dÃ©pend du rÃ©seau/environnement).
- [ ] Validation terrain/agronome des recommandations et des notes de rotation.
- [ ] Envoi SMS/USSD rÃ©el via fournisseur, file Celery avec Redis/worker et durcissement des accÃ¨s (hors pÃ©rimÃ¨tre dÃ©mo).

## Avertissement

AgroSentry fournit des indicateurs dâ€™aide Ã  la dÃ©cision Ã  partir de donnÃ©es et de modÃ¨les imparfaits. **Ne jamais prendre de dÃ©cision agronomique ou Ã©conomique sur la seule base de cet outil** : confronter les rÃ©sultats aux observations locales et Ã  lâ€™avis dâ€™un agronome.

