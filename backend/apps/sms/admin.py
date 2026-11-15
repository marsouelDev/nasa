"""Administration du journal SMS."""

from django.contrib import admin

from .models import EnvoiSMS


@admin.register(EnvoiSMS)
class EnvoiSMSAdmin(admin.ModelAdmin):
    list_display = ("destinataire", "categorie", "statut", "mode", "longueur", "cree_le")
    list_filter = ("statut", "mode", "categorie")
    search_fields = ("destinataire", "message", "reference")
    readonly_fields = (
        "agriculteur",
        "destinataire",
        "message",
        "longueur",
        "statut",
        "mode",
        "categorie",
        "reference",
        "erreur",
        "cree_le",
    )
    date_hierarchy = "cree_le"

    def has_add_permission(self, request) -> bool:
        return False
