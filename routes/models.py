from django.db import models
from django.utils import timezone

# Create your models here.

class RouteTemplate(models.Model):
    """Template for reusable route paths"""
    name = models.CharField(max_length=200, unique=True)
    description = models.TextField(blank=True)
    source_station = models.ForeignKey('stations.Station', 
                                       on_delete=models.CASCADE, 
                                       related_name='route_templates_source')
    destination_station = models.ForeignKey('stations.Station', 
                                            on_delete=models.CASCADE, 
                                            related_name='route_templates_destination')
    total_distance = models.FloatField(help_text="Total distance in km")
    estimated_duration = models.IntegerField(help_text="Estimated duration in minutes")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} ({self.source_station.code} - {self.destination_station.code})"

    class Meta:
        verbose_name = 'Route Template'
        verbose_name_plural = 'Route Templates'
        ordering = ['name']

class RouteTemplateStop(models.Model):
    """Predefined stops for route templates"""
    route_template = models.ForeignKey(RouteTemplate, on_delete=models
                                       .CASCADE, related_name='template_stops')
    station = models.ForeignKey('stations.Station', on_delete=models
                                .CASCADE, related_name='template_stops')
    sequence = models.PositiveIntegerField(
        help_text="Order of stops in the template")
    distance_from_source = models.FloatField(
                            help_text="Distance from source station in km")
    estimated_halt_minutes = models.PositiveIntegerField(
                            default=2, help_text="Estimated halt duration")

    def __str__(self):
        return f"{self.route_template.name} - {self.station.name} (Seq: {self.sequence})"

    class Meta:
        verbose_name = 'Route Template Stop'
        verbose_name_plural = 'Route Template Stops'
        unique_together = ('route_template', 'sequence')
        ordering = ['route_template', 'sequence']

class TrainRouteStop(models.Model):
    """
    Represents a train stopping at a station
    """
    train = models.ForeignKey('trains.Train', on_delete=models.CASCADE,
                              related_name='route_stops')
    station = models.ForeignKey('stations.Station', on_delete=models
                                .CASCADE, related_name='train_stops')
    sequence = models.PositiveIntegerField(help_text="Order of stops (1, 2, 3...)")
    # Scheduled times
    scheduled_arrival_time = models.TimeField(null=True,blank=True,
                                              help_text="Scheduled arrival time (null for source station)")
    scheduled_departure_time = models.TimeField(null=True, blank=True, 
                                                help_text="Scheduled departure time (null for destination station)")
    # Actual times (to be updated by station master)
    actual_arrival_time = models.TimeField(null=True, blank=True, 
                                           help_text="Actual arrival time (null for source station)")
    actual_departure_time = models.TimeField(null=True, blank=True, 
                                             help_text="Actual departure time (null for destination station)")
    halt_minutes = models.PositiveIntegerField(default=0, 
                                               help_text="Halt duration in minutes")
    distance_from_source = models.FloatField(help_text="Distance from source station in km")
    day_count = models.PositiveIntegerField(default=1,
                                            help_text="Day count (1 for same day, 2 for next day, etc.)")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.train.name} - {self.station.name} (Seq: {self.sequence})"

    class Meta:
        verbose_name = 'Train Route Stop'
        verbose_name_plural = 'Train Route Stops'
        unique_together = ('train', 'sequence')
        ordering = ['train', 'sequence']
