# Mission : construire l'application AgroSentry (Bafia, Cameroun)

Tu es un développeur senior. Tu construis le MVP d'AgroSentry, un outil d'aide à la décision agro-climatique pour de petits agriculteurs : calendrier de semis et comparaison de 3 stratégies de rotation des cultures, à partir de données NASA, avec une carte 3D interactive et une passerelle SMS/USSD simulée.

## 0. Avant d'écrire du code (obligatoire)

1. Lis `AGENTS.md`, `cahier.md` (ou `cahier.txt`, export du cahier des charges), `nasa_power_edea.py`, `agrosentry_model.py` et `agrosentry_carte_gibs.html` s'ils sont présents.
2. Ignore totalement `download-all-*.py` (script ASF/NISAR, inutile pour ce projet). Ne le lance pas, ne le modifie pas.
3. Vérifie les versions de Python et de Node installées (`python --version`, `node --version`) et dis-moi si quelque chose manque.
4. Propose un plan détaillé par phases et **attends mon accord avant de créer ou modifier un fichier**.
5. Initialise un dépôt git s'il n'existe pas, et fais un commit par phase.

## Règles générales

- Stack imposée : **backend Django + Django REST Framework**, **frontend React (Vite)**. Pas de FastAPI.
- Tout ce qui est visible par l'utilisateur est en **français**. Identifiants de code en anglais, commentaires en français.
- Outils gratuits uniquement, sans clé payante. Aucune clé ni mot de passe dans le code : utilise un fichier `.env` (non versionné) et fournis `.env.example`.
- Utilise un environnement virtuel Python (`venv`) et `requirements.txt`. Les commandes doivent marcher sous **Windows (PowerShell)**.
- Connexion lente : privilégie des téléchargements légers, un cache local des données NASA et un **mode léger** (carte 2D, sans terrain 3D).
- **Honnêteté des données** : n'invente aucune mesure. Toute valeur simulée ou estimée doit être étiquetée « démonstration » à l'écran et dans l'API (champ `source`). Distingue donnée NASA réelle, calcul du modèle et valeur illustrative.
- Chaque recommandation affiche un **niveau de confiance** (faible, moyenne, élevée) et la mention « à valider avec un agronome ».
- À la fin de chaque phase : lance les tests, donne les commandes pour essayer le résultat, puis **arrête-toi** et attends ma validation.

## Phase 1 : backend Django

Crée le projet `backend/` avec les applications `data`, `ml`, `rotations`, `sms`, `accounts`.

- **Zone pilote : Bafia, latitude 4,75, longitude 11,23** (configurable dans un modèle `Zone`, pas codée en dur). Le script `nasa_power_edea.py` vise Edéa : ne reprends que sa logique, pas ses coordonnées.
- Commande `python manage.py ingest_power` : télécharge les données **NASA POWER** journalières (API `https://power.larc.nasa.gov/api/temporal/daily/point`, communauté `AG`, paramètres `PRECTOTCORR,T2M_MAX,T2M_MIN`, de 2016 à la dernière date disponible). Gère les valeurs manquantes (`-999`), les erreurs réseau, les nouvelles tentatives, et enregistre en base (ORM) avec cache pour ne pas retélécharger. Export CSV en UTF-8.
- API REST (préfixe `/api/`) : `zones/`, `pluie/` (série et début de saison), `risques/` (risque de poche de sécheresse), `calendrier-semis/`, `rotations/`, `point/?lat=&lon=` (valeurs locales pour un clic sur la carte), `sms/campagnes/`, `ussd/` (webhook).
- CORS limité au domaine du frontend, authentification par jeton pour les routes d'écriture, documentation OpenAPI.
- SQLite en développement, configuration prête pour PostgreSQL via variable d'environnement.
- Tests automatiques (pytest ou `manage.py test`) pour l'ingestion (avec réponses simulées), les endpoints et le moteur de rotation.

## Phase 2 : modèle ML (app `ml`)

- Intègre la logique de `agrosentry_model.py` : détection du début de saison des pluies (règle explicable) et **Random Forest** de risque de poche de sécheresse à 15 jours, avec validation temporelle (`TimeSeriesSplit`) et importance des variables.
- Commande `python manage.py train_models` qui sauvegarde le modèle (`joblib`) et affiche les scores. Pas de deep learning.
- Les endpoints renvoient la prédiction, les variables qui l'expliquent et le niveau de confiance.

## Phase 3 : moteur de rotation (app `rotations`)

- Compare 3 scénarios pour Bafia : **S0 rotation actuelle (référence), S1 maïs puis légumineuse (arachide, niébé, soja), S2 maïs puis culture de couverture (ex. mucuna)**.
- Fiches cultures et notes (0 à 10) par critère dans des **fixtures JSON modifiables** : économie d'eau, protection contre l'érosion, matière organique, azote, rupture des ravageurs, revenu, facilité de travail. Ces notes sont des hypothèses à valider par un agronome : écris-le dans les données.
- Score pondéré explicable selon les priorités de l'utilisateur (eau, sol, revenu, travail) et un scénario de pluie de −30 % à +30 %. La réponse contient, pour chaque scénario : score, contributions par critère, **pourquoi proposée, données à l'appui, bénéfices, lacunes d'information, risques à évaluer localement**, et le niveau de confiance (faible si l'écart entre scénarios est petit ou si le scénario climatique est extrême).

## Phase 4 : frontend React (Vite, PWA)

Crée `frontend/` avec les pages **Carte**, **Tendances** (saison en cours comparée à dix ans, graphiques Chart.js), **Rotations** (comparateur avec curseurs de priorités), **Console SMS**. Gère les états de chargement et d'erreur, l'accessibilité (jamais de couleur seule, légendes avec unités) et le responsive mobile. Configure le manifest PWA et le service worker.

### Carte 3D de type Google Maps (page Carte)

Utilise **MapLibre GL JS** (open source, sans clé). Google Maps 3D réel nécessite une clé payante : ne l'utilise pas.

- Vue initiale : centre `[11.23, 4.75]`, zoom 11, inclinaison (pitch) 60, rotation (bearing) −20, inclinaison maximale 85.
- **Relief 3D** : source `raster-dem` avec les tuiles `https://s3.amazonaws.com/elevation-tiles-prod/terrarium/{z}/{x}/{y}.png` (encodage `terrarium`, maxzoom 15), `map.setTerrain({ source: 'dem', exaggeration: 1.5 })` et une couche d'ombrage du relief (hillshade). Ajoute ciel et atmosphère si la version de MapLibre le permet.
- **Fonds de carte** commutables : « Plan » (style vectoriel gratuit, par exemple OpenFreeMap, sinon tuiles raster CARTO Voyager) et « Satellite » (Esri World Imagery). Bâtiments en extrusion 3D si le style choisi les fournit.
- **Couches NASA GIBS réelles** (tuiles WMTS EPSG:3857, modèle `https://gibs.earthdata.nasa.gov/wmts/epsg3857/best/{LAYER}/default/{DATE}/{TILEMATRIXSET}/{z}/{y}/{x}.{EXT}`), activables avec curseur d'opacité et sélecteur de date :
  - `MODIS_Terra_NDVI_8Day` (GoogleMapsCompatible_Level9, png) : aligne la date sur le composite de 8 jours (début au 1er janvier de chaque année) ;
  - `MODIS_Terra_Land_Surface_Temp_Day` (GoogleMapsCompatible_Level7, png) ;
  - `MODIS_Terra_CorrectedReflectance_TrueColor` (GoogleMapsCompatible_Level9, jpg).
    Règle `maxzoom` de chaque source sur le niveau natif pour éviter les tuiles vides, et vérifie que chaque couche s'affiche réellement avant de dire qu'elle fonctionne.
- Contrôles : zoom/rotation/inclinaison (NavigationControl avec visualisation du pitch), échelle, plein écran, bouton **2D/3D**, bouton **mode léger**, panneau des couches, légende avec unité et date.
- **Clic sur la carte** : marqueur, appel `GET /api/point/?lat=&lon=` et fenêtre d'information (pluie récente, température, risque, meilleure rotation avec confiance). Affiche uniquement des valeurs que l'API peut fournir ; marque le reste « démonstration ».
- Affiche les attributions (OpenStreetMap, CARTO ou OpenFreeMap, Esri, NASA GIBS).
- Prévois l'échec réseau : message clair et retour automatique au fond de carte disponible.

## Phase 5 : SMS et USSD (simulés)

- Webhook USSD et SMS compatibles avec le format d'Africa's Talking, vérifiés mais **sans appel réel** tant que les clés ne sont pas configurées : fournis un **simulateur** (page ou commande) qui affiche le SMS qui serait envoyé.
- Messages de 160 caractères au plus, en français, avec confiance et mention de validation. Campagnes planifiées avec Celery (Redis optionnel : prévois un mode sans Redis pour le développement).
- Collecte minimale de données personnelles, consentement enregistré.

## Phase 6 : finition

- `README.md` en français : installation, lancement du backend et du frontend sous Windows, variables d'environnement, commandes `ingest_power` et `train_models`.
- Lint et formatage (ruff ou flake8, ESLint), tests qui passent, et liste des limites connues (données SMAP/MODIS en série temporelle non branchées, notes de rotation à valider, mode hors ligne partiel).
- Mets à jour `AGENTS.md` avec les commandes réelles du projet.

## Critères d'acceptation du MVP

1. `ingest_power` remplit la base avec des données réelles de Bafia.
2. La carte 3D s'ouvre sur Bafia avec relief, bascule Plan/Satellite et au moins la couche NDVI réelle visible.
3. Un clic sur la carte affiche des valeurs issues de l'API avec leur source.
4. Le comparateur affiche 3 rotations avec les 5 rubriques et le niveau de confiance.
5. Le simulateur produit un SMS de 160 caractères au plus.
6. Tous les tests passent et le README permet de tout relancer depuis zéro.
