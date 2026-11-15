"""Administration des zones et des données météo."""

from django.contrib import admin

from .models import DailyWeather, IngestionLog, Zone


@admin.register(Zone)
class ZoneAdmin(admin.ModelAdmin):
    list_display = ("nom", "slug", "pays", "latitude", "longitude", "actif")
    list_filter = ("actif", "pays")
    search_fields = ("nom", "slug")
    prepopulated_fields = {"slug": ("nom",)}


@admin.register(DailyWeather)
class DailyWeatherAdmin(admin.ModelAdmin):
    list_display = ("zone", "date", "precip_mm", "tmax_c", "tmin_c", "source")
    list_filter = ("zone", "source")
    date_hierarchy = "date"
    search_fields = ("zone__nom",)


@admin.register(IngestionLog)
class IngestionLogAdmin(admin.ModelAdmin):
    list_display = ("zone", "debut", "fin", "statut", "jours_recus", "jours_ignores", "cree_le")
    list_filter = ("statut", "zone")
    readonly_fields = ("cree_le", "termine_le")
