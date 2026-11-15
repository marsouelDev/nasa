"""Migration de données : zone pilote Bafia (modifiable ensuite dans l'admin)."""

from django.db import migrations


def creer_bafia(apps, schema_editor):
    Zone = apps.get_model("data", "Zone")
    Zone.objects.get_or_create(
        slug="bafia",
        defaults={
            "nom": "Bafia",
            "pays": "Cameroun",
            "latitude": 4.75,
            "longitude": 11.23,
            "actif": True,
        },
    )


class Migration(migrations.Migration):
    dependencies = [("data", "0001_initial")]

    operations = [migrations.RunPython(creer_bafia, migrations.RunPython.noop)]
