"""Administration des agriculteurs et des consentements."""

from django.contrib import admin

from .models import Agriculteur


@admin.register(Agriculteur)
class AgriculteurAdmin(admin.ModelAdmin):
    list_display = (
        "telephone",
        "nom",
        "zone",
        "langue",
        "consentement",
        "consentement_le",
        "desinscrit_le",
        "actif",
    )
    list_filter = ("consentement", "langue", "zone", "actif")
    search_fields = ("telephone", "nom")
    readonly_fields = (
        "consentement_le",
        "consentement_version",
        "consentement_texte",
        "desinscrit_le",
        "cree_le",
        "maj_le",
    )
    date_hierarchy = "cree_le"
