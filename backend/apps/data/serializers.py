"""Sérialiseurs de l'API data."""

from rest_framework import serializers

from .models import DailyWeather, Zone


class ZoneSerializer(serializers.ModelSerializer):
    class Meta:
        model = Zone
        fields = ("id", "nom", "slug", "pays", "latitude", "longitude", "altitude_m")


class DailyWeatherSerializer(serializers.ModelSerializer):
    class Meta:
        model = DailyWeather
        fields = ("date", "precip_mm", "tmax_c", "tmin_c")
