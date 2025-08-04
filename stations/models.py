from django.conf import settings
from django.db import models
from utils.validators import StationValidators


class ActiveManager(models.Manager):
    """Manager that returns only active records"""

    def get_queryset(self):
        return super().get_queryset().filter(is_active=True)

class Station(models.Model):
    """
    Represents a railway station with code, city, state, and status.
    Supports soft delete via is_active.
    Uses centralized validators for consistency.
    """

    name = models.CharField(max_length=100, db_index=True)
    code = models.CharField(max_length=5, unique=True, db_index=True)
    city = models.CharField(max_length=100, db_index=True)
    state = models.CharField(max_length=100, db_index=True)
    is_active = models.BooleanField(
        default=True, help_text="Indicates if the station is active or not", db_index=True
    )
    station_master = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        limit_choices_to={"role": "station_master", "is_active": True},
        related_name="station",
        help_text="Assign a user with role=station_master and is_active=True",
    )
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Managers
    objects = ActiveManager()
    all_objects = models.Manager()

    def clean(self):
        """
        Validates station code, uniqueness, and station master assignment.
        Uses centralized validators for consistency.
        """
        # Use centralized validators
        if self.code:
            self.code = StationValidators.validate_station_code(self.code, self.pk)
        
        if self.name:
            self.name = StationValidators.validate_station_name(self.name, self.pk)
        
        # Validate station master assignment
        if self.station_master:
            StationValidators.validate_station_master_assignment(
                self.station_master.id, self
            )

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
        verbose_name = "Station"
        verbose_name_plural = "Stations"
        ordering = ["code"]
        indexes = [
            models.Index(fields=['code', 'is_active']),
            models.Index(fields=['city', 'state']),
            models.Index(fields=['station_master', 'is_active']),
        ]
