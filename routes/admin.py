from django.contrib import admin
from .models import TrainRouteStop, RouteTemplate, RouteTemplateStop

class RouteTemplateStopInline(admin.TabularInline):
    model = RouteTemplateStop
    extra = 1
    ordering = ['sequence']

class TrainRouteStopInline(admin.TabularInline):
    model = TrainRouteStop
    extra = 1
    ordering = ['sequence']

@admin.register(RouteTemplate)
class RouteTemplateAdmin(admin.ModelAdmin):
    list_display = ('name', 'source_station', 'destination_station', 'total_distance', 'estimated_duration')
    list_filter = ('source_station', 'destination_station')
    search_fields = ('name', 'source_station__name', 'destination_station__name')
    readonly_fields = ('created_at', 'updated_at')
    inlines = [RouteTemplateStopInline]

@admin.register(RouteTemplateStop)
class RouteTemplateStopAdmin(admin.ModelAdmin):
    list_display = ('route_template', 'station', 'sequence', 'distance_from_source', 'estimated_halt_minutes')
    list_filter = ('route_template', 'station')
    search_fields = ('route_template__name', 'station__name', 'station__code')
    ordering = ['route_template', 'sequence']

@admin.register(TrainRouteStop)
class TrainRouteStopAdmin(admin.ModelAdmin):
    list_display = ('train', 'station', 'sequence', 'arrival_time', 'departure_time', 'halt_minutes', 'day_count')
    list_filter = ('train', 'station', 'day_count')
    search_fields = ('train__name', 'train__train_number', 'station__name', 'station__code')
    ordering = ['train', 'sequence']
    readonly_fields = ('created_at', 'updated_at')
