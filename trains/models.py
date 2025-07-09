from django.db import models
from django.contrib.postgres.fields import ArrayField
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
        ('Express', 'Express'),
        ('Passenger', 'Passenger'),
        ('Superfast', 'Superfast'),
    ]
    
    RUNNING_DAYS_CHOICES = [
        ('Mon', 'Monday'),
        ('Tue', 'Tuesday'),
        ('Wed', 'Wednesday'),
        ('Thu', 'Thursday'),
        ('Fri', 'Friday'),
        ('Sat', 'Saturday'),
        ('Sun', 'Sunday'),
    ]
    
    train_number = models.CharField(max_length=10, unique=True, blank=True)
    name = models.CharField(max_length=200)
    train_type = models.CharField(max_length=20, choices=TRAIN_TYPE_CHOICES)
    running_days = ArrayField(
        models.CharField(max_length=3, choices=RUNNING_DAYS_CHOICES),
        size=7,
        help_text="Days when the train runs (e.g., ['Mon', 'Tue', 'Fri'])"
    )
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
        verbose_name = 'Train'
        verbose_name_plural = 'Trains'
        ordering = ['train_number']

class TrainClass(models.Model):
    """
    Represents a class (e.g., AC, Sleeper) and seat capacity for a train.
    """
    CLASS_TYPE_CHOICES = [
        ('General', 'General'),
        ('Sleeper', 'Sleeper'),
        ('AC', 'AC'),
    ]
    
    train = models.ForeignKey(Train, on_delete=models.CASCADE, related_name='classes')
    class_type = models.CharField(max_length=20, choices=CLASS_TYPE_CHOICES)
    seat_capacity = models.PositiveIntegerField(help_text="Number of seats available in this class")

    def __str__(self):
        return f"{self.train.name} - {self.class_type} ({self.seat_capacity} seats)"

    class Meta:
        verbose_name = 'Train Class'
        verbose_name_plural = 'Train Classes'
        unique_together = ('train', 'class_type')
        ordering = ['train', 'class_type']
