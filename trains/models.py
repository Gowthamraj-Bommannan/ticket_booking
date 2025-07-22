from django.db import models
from routes.models import RouteTemplate
import random

class ActiveManager(models.Manager):
    """Manager that returns only active records"""
    def get_queryset(self):
        return super().get_queryset().filter(is_active=True)

class Train(models.Model):
    """
    Represents a train with its number, name, type, running days, and status.
    Supports soft delete via is_active.
    """
    TRAIN_TYPE_CHOICES = [
        ('Local', 'local'),
        ('Fast', 'fast'),
        ('AC', 'ac')
    ]
    
    train_number = models.CharField(max_length=10, unique=True, blank=True)
    name = models.CharField(max_length=200)
    train_type = models.CharField(max_length=20, choices=TRAIN_TYPE_CHOICES)
    is_active = models.BooleanField(default=True, help_text="Indicates if the train is active or soft deleted")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Managers
    objects = ActiveManager()  # Returns only active records
    all_objects = models.Manager()  # Returns all records including inactive

    def generate_train_number(self):
        """
        Generates a unique 5-digit train number for new trains.
        """
        while True:
            # Generate a random 5-digit number
            train_number = str(random.randint(10000, 99999))
            # Check if it's already used
            if not Train.all_objects.filter(train_number=train_number).exists():
                return train_number

    def save(self, *args, **kwargs):
        """
        Saves the train, auto-generating a train number if needed.
        """
        # Auto-generate train number if not provided
        if not self.train_number:
            self.train_number = self.generate_train_number()
        
        super().save(*args, **kwargs)

    def __str__(self):
        """
        Returns a string representation of the train, including inactive status.
        """
        status = " (Inactive)" if not self.is_active else ""
        return f"{self.name} ({self.train_number}){status}"

    class Meta:
        db_table = 'trains'
        verbose_name = 'Train'
        verbose_name_plural = 'Trains'
        ordering = ['train_number']

class TrainClass(models.Model):
    """
    Represents a class (e.g., AC, Sleeper) and seat capacity for a train.
    """
    CLASS_TYPE_CHOICES = [
        ('GENERAL', 'General'),
        ('FC', 'fc'),
    ]
    train = models.ForeignKey(Train, on_delete=models.CASCADE, related_name='classes')
    class_type = models.CharField(max_length=20, choices=CLASS_TYPE_CHOICES)

    def __str__(self):
        return f"{self.train.name} - {self.class_type})"

    class Meta:
        db_table = 'train_class'
        verbose_name = 'Train Class'
        verbose_name_plural = 'Train Classes'
        unique_together = ('train', 'class_type')
        ordering = ['train', 'class_type']

class TrainSchedule(models.Model):
    train = models.ForeignKey(Train, on_delete=models.CASCADE, related_name='schedules')
    route_template = models.ForeignKey(RouteTemplate, on_delete=models.CASCADE)
    days_of_week = models.CharField(max_length=20)
    start_time = models.TimeField()
    stops_with_time = models.JSONField(default=list, blank=True)
    direction = models.CharField(max_length=10, choices=[('up', 'Up'), ('down', 'Down')])
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'train_schedules'
        verbose_name = 'Train Schedule'
        verbose_name_plural = 'Train Schedules'
        ordering = ['train', 'start_time']

    def __str__(self):
        return f"{self.train} on {self.route_template} at {self.start_time}"