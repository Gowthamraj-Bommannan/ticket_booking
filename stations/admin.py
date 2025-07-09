from django.contrib import admin
from .models import Station

@admin.register(Station)
class StationAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'city', 'state', 'station_master')
    search_fields = ('name', 'code', 'city', 'state')
    autocomplete_fields = ['station_master']
