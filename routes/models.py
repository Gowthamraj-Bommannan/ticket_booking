from django.db import models
from stations.models import Station

class RouteEdge(models.Model):
    """
    Represents a direct connection (edge) between two stations.
    Used for route pathfinding and validation.
    """
    from_station = models.ForeignKey(Station, on_delete=models.CASCADE, related_name='edges_from')
    to_station = models.ForeignKey(Station, on_delete=models.CASCADE, related_name='edges_to')
    distance = models.PositiveIntegerField()
    is_bidirectional = models.BooleanField(default=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('from_station', 'to_station', 'is_active')
        db_table = 'route_graph'

    def __str__(self):
        return f"{self.from_station} to {self.to_station} ({self.distance} km)"
    
class RouteTemplate(models.Model):
    """
    Template for a train route, including stops and category.
    Used to generate train schedules.
    """
    CATEGORY_CHOICES = [
        ('local', 'local'),
        ('fast', 'fast')
    ]

    name = models.CharField(max_length=100)
    from_station = models.ForeignKey(Station, related_name='template_starts',
                                     on_delete=models.CASCADE)
    to_station = models.ForeignKey(Station, related_name='template_ends',
                                   on_delete=models.CASCADE)
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES)
    stops = models.JSONField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    update_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['from_station', 'to_station', 'category']
        db_table = 'templates'

    def __str__(self):
        return f"{self.name} {self.from_station} {self.to_station} {self.category}"