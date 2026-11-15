"""Configuration Django d'AgroSentry.

Les valeurs sensibles viennent du fichier .env à la racine du dépôt.
En développement, des valeurs par défaut permettent de lancer le projet
sans configuration supplémentaire.
"""

import os
from pathlib import Path

from django.core.exceptions import ImproperlyConfigured
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent  # backend/
ROOT_DIR = BASE_DIR.parent  # racine du dépôt
load_dotenv(ROOT_DIR / ".env")


def env_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "oui", "on"}


def env_list(name: str, default: str = "") -> list[str]:
    return [item.strip() for item in os.getenv(name, default).split(",") if item.strip()]


# --- Sécurité -------------------------------------------------------------
DEBUG = env_bool("DJANGO_DEBUG", True)
SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", "")
if not SECRET_KEY:
    if DEBUG:
        SECRET_KEY = "dev-secret-insecure-uniquement-pour-le-developpement"
    else:
        raise ImproperlyConfigured("DJANGO_SECRET_KEY doit être défini quand DJANGO_DEBUG=False.")

ALLOWED_HOSTS = env_list("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1")
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5173")

# Origines front autorisées : CORS et CSRF partagent la même variable
# d'environnement, définie une seule fois ici.
FRONTEND_ORIGINS = env_list(
    "CORS_ALLOWED_ORIGINS",
    "http://localhost:5173,http://127.0.0.1:5173,http://localhost:5174,http://127.0.0.1:5174",
)
CSRF_TRUSTED_ORIGINS = FRONTEND_ORIGINS

# --- Applications ---------------------------------------------------------
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "rest_framework.authtoken",
    "corsheaders",
    "drf_spectacular",
    "apps.accounts",
    "apps.data",
    "apps.ml",
    "apps.rotations",
    "apps.sms",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "agrosentry.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "agrosentry.wsgi.application"
ASGI_APPLICATION = "agrosentry.asgi.application"

# --- Base de données ------------------------------------------------------
if os.getenv("DB_ENGINE", "sqlite").lower() in {"postgres", "postgresql"}:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": os.getenv("DB_NAME", "agrosentry"),
            "USER": os.getenv("DB_USER", "agrosentry"),
            "PASSWORD": os.getenv("DB_PASSWORD", ""),
            "HOST": os.getenv("DB_HOST", "localhost"),
            "PORT": os.getenv("DB_PORT", "5432"),
            "CONN_MAX_AGE": 60,
        }
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }

# --- Authentification -----------------------------------------------------
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.TokenAuthentication",
        "rest_framework.authentication.SessionAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        # Lecture publique, écriture réservée aux comptes authentifiés.
        "rest_framework.permissions.IsAuthenticatedOrReadOnly",
    ],
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
}

SPECTACULAR_SETTINGS = {
    "TITLE": "API AgroSentry",
    "DESCRIPTION": (
        "API de démonstration AgroSentry (Bafia, Cameroun) : météo NASA POWER, "
        "risque de poche de sécheresse, calendrier de semis et rotations."
    ),
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
    "COMPONENT_SPLIT_REQUEST": True,
}

# --- CORS (frontend React servi séparément) -------------------------------
CORS_ALLOWED_ORIGINS = FRONTEND_ORIGINS
if DEBUG:
    # En développement, tout port local est accepté : Vite change de port
    # (5174, 5175...) quand 5173 est déjà pris. En production (DEBUG=False),
    # seule la liste explicite ci-dessus reste active.
    CORS_ALLOWED_ORIGIN_REGEXES = [
        r"^http://localhost:\d+$",
        r"^http://127\.0\.0\.1:\d+$",
    ]
CORS_ALLOW_CREDENTIALS = False

# --- Internationalisation -------------------------------------------------
LANGUAGE_CODE = "fr-fr"
TIME_ZONE = "Africa/Douala"
USE_I18N = True
USE_TZ = True

# --- Fichiers statiques ---------------------------------------------------
STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
MEDIA_URL = "media/"
MEDIA_ROOT = BASE_DIR / "media"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# --- Paramètres métier ----------------------------------------------------
DEFAULT_ZONE_SLUG = os.getenv("DEFAULT_ZONE_SLUG", "bafia")
POWER_API_URL = os.getenv(
    "POWER_API_URL", "https://power.larc.nasa.gov/api/temporal/daily/point"
)
POWER_TIMEOUT = int(os.getenv("POWER_TIMEOUT", "120"))
POWER_MAX_RETRIES = int(os.getenv("POWER_MAX_RETRIES", "3"))
# POWER renvoie cette valeur sentinelle pour les jours sans donnée.
POWER_FILL_VALUE = -999

# --- Africa's Talking / SMS (phase 5) ------------------------------------
# Par défaut, tout est simulé : aucun message n'est transmis. Pour un envoi
# réel il faut des clés ET passer SMS_SIMULATION=False ET SMS_ENVOI_REEL=True.
AT_USERNAME = os.getenv("AT_USERNAME", "")
AT_API_KEY = os.getenv("AT_API_KEY", "")
AT_SENDER_ID = os.getenv("AT_SENDER_ID", "")
AT_API_URL = os.getenv(
    "AT_API_URL", "https://api.africastalking.com/version1/messaging"
)
SMS_SIMULATION = env_bool("SMS_SIMULATION", True)
SMS_ENVOI_REEL = env_bool("SMS_ENVOI_REEL", False)

# --- Celery (phase 5) -----------------------------------------------------
# Mode eager par défaut en développement : les tâches s'exécutent immédiatement
# (envoi des alertes SMS). Pas besoin de Redis local pour la démo.
CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL", "memory://")
CELERY_TASK_ALWAYS_EAGER = env_bool("CELERY_TASK_ALWAYS_EAGER", True)
CELERY_TASK_EAGER_PROPAGATES = True
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND", "cache+memory://")

# --- Journalisation -------------------------------------------------------
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "simple": {"format": "[{levelname}] {name} : {message}", "style": "{"},
    },
    "handlers": {
        "console": {"class": "logging.StreamHandler", "formatter": "simple"},
    },
    "loggers": {
        "apps": {"handlers": ["console"], "level": "INFO", "propagate": False},
    },
}