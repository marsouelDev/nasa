"""Application Celery d'AgroSentry.

Mode développement : `CELERY_TASK_ALWAYS_EAGER=True` (défaut du dépôt),
broker mémoire. L'envoi de SMS d'alerte s'exécute donc directement à la
réception de la tâche, sans Redis.
"""

from celery import Celery

app = Celery("agrosentry")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()
