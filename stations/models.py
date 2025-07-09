from django.conf import settings
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.apps import apps
from django.db import models

class ActiveManager(models.Manager):
    """Manager that returns only active records"""
    def get_queryset(self):
        return super().get_queryset().filter(is_active=True)

# Create your models here.

class Station(models.Model):
    """
    Represents a railway station with code, city, state, and status.
    Supports soft delete via is_active.
    """
    name = models.CharField(max_length=100)
    code = models.CharField(max_length=5, unique=True)
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    is_active = models.BooleanField(default=True, help_text="Indicates if the station is active or soft deleted")
    station_master = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        limit_choices_to={'role': 'station_master', 'is_staff': True, 'is_active': True},
        related_name='station',
        help_text='Assign a user with role=station_master, is_staff=True, and is_active=True.'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Managers
    objects = ActiveManager()  # Returns only active records
    all_objects = models.Manager()  # Returns all records including inactive

    def clean(self):
        """
        Validates station code, uniqueness, and station master assignment.
        """
        # Code must be uppercase, unique (case-insensitive), and 2-5 chars
        if not (2 <= len(self.code) <= 5):
            raise ValidationError({'code': 'Code must be 2-5 characters.'})
        if self.code != self.code.upper():
            raise ValidationError({'code': 'Code must be uppercase.'})
        if Station.all_objects.exclude(pk=self.pk).filter(code__iexact=self.code).exists():
            raise ValidationError({'code': 'Station code must be unique (case-insensitive).'})
        # Station master validation - check is_active first, then role and is_staff
        if self.station_master:
            if not self.station_master.is_active:
                raise ValidationError({'station_master': 'User must be active (is_active=True).'})
            if self.station_master.role != 'station_master' or not self.station_master.is_staff:
                raise ValidationError({'station_master': 'User must have role=station_master and is_staff=True.'})
            if Station.all_objects.exclude(pk=self.pk).filter(station_master=self.station_master).exists():
                raise ValidationError({'station_master': 'This user is already assigned as a station master to another station.'})

    def save(self, *args, **kwargs):
        """
        Saves the station, ensuring code is uppercase and valid.
        """
        self.code = self.code.upper()
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        """
        Returns a string representation of the station, including inactive status.
        """
        status = " (Inactive)" if not self.is_active else ""
        return f"{self.name} ({self.code}){status}"

    class Meta:
        verbose_name = 'Station'
        verbose_name_plural = 'Stations'
        ordering = ['code']
