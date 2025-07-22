from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone

User = get_user_model()

class Booking(models.Model):
    """
    Booking model for train reservations.
    Stores passenger, train, and payment details.
    """

    CLASS_CHOICES = [
        ('GENERAL', 'General'),
        ('FC', 'First Class')
    ]

    BOOKING_STATUS_CHOICES = [
        ('BOOKED', 'Booked'),
        ('FAILED', 'Failed'),
        ('PENDING', 'Pending'),
    ]
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='bookings')
    from_station = models.ForeignKey('stations.Station', on_delete=models.CASCADE, related_name='source_bookings')
    to_station = models.ForeignKey('stations.Station', on_delete=models.CASCADE, related_name='destination_bookings')
    class_type = models.CharField(max_length=20, choices=CLASS_CHOICES, default='General')
    num_of_passenegers = models.PositiveIntegerField()
    total_fare = models.DecimalField(max_digits=8, decimal_places=2)
    booking_time = models.DateTimeField(auto_now_add=True)
    expiry_time = models.DateTimeField()
    travel_date = models.DateField(default=timezone.now)
    ticket_number = models.CharField(max_length=8, unique=True, blank=True)
    booking_status = models.CharField(max_length=20, choices=BOOKING_STATUS_CHOICES, default='PENDING')

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    @property
    def is_expired(self):
        return timezone.now() > self.expiry_time

    def __str__(self):
        return f"Ticket number: {self.ticket_number} - {self.class_type} - {self.user.username}"

    class Meta:
        ordering = ['-booking_time']
        verbose_name = 'Booking'
        verbose_name_plural = 'Bookings'
        db_table = 'booking'
