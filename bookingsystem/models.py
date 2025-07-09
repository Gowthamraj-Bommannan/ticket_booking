from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone
import random
import string

User = get_user_model()

class Booking(models.Model):
    """Booking model for train reservations"""
    
    BOOKING_STATUS_CHOICES = [
        ('CONFIRMED', 'Confirmed'),
        ('RAC', 'Reservation Against Cancellation'),
        ('WL', 'Waitlist'),
        ('CANCELLED', 'Cancelled'),
    ]
    
    QUOTA_CHOICES = [
        ('General', 'General'),
        ('Tatkal', 'Tatkal'),
        ('Ladies', 'Ladies'),
        ('SeniorCitizen', 'Senior Citizen'),
    ]
    
    CLASS_TYPE_CHOICES = [
        ('General', 'General'),
        ('Sleeper', 'Sleeper'),
        ('AC', 'AC'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='bookings')
    train = models.ForeignKey('trains.Train', on_delete=models.CASCADE, related_name='bookings')
    source_station = models.ForeignKey('stations.Station', on_delete=models.CASCADE, related_name='source_bookings')
    destination_station = models.ForeignKey('stations.Station', on_delete=models.CASCADE, related_name='destination_bookings')
    travel_date = models.DateField()
    booking_status = models.CharField(max_length=20, choices=BOOKING_STATUS_CHOICES, default='PENDING')
    quota = models.CharField(max_length=20, choices=QUOTA_CHOICES, default='General')
    class_type = models.CharField(max_length=20, choices=CLASS_TYPE_CHOICES, default='Sleeper')
    total_fare = models.DecimalField(max_digits=10, decimal_places=2)
    pnr_number = models.CharField(max_length=10, unique=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        if not self.pnr_number:
            self.pnr_number = self.generate_pnr()
        super().save(*args, **kwargs)

    def generate_pnr(self):
        """Generate unique 10-digit PNR number"""
        while True:
            pnr = ''.join(random.choices(string.digits, k=10))
            if not Booking.objects.filter(pnr_number=pnr).exists():
                return pnr

    def __str__(self):
        return f"PNR: {self.pnr_number} - {self.user.username}"

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Booking'
        verbose_name_plural = 'Bookings'

class Passenger(models.Model):
    """Passenger model for individual passengers in a booking"""
    
    GENDER_CHOICES = [
        ('Male', 'Male'),
        ('Female', 'Female'),
        ('Other', 'Other'),
    ]
    
    BERTH_PREFERENCE_CHOICES = [
        ('LB', 'Lower Berth'),
        ('MB', 'Middle Berth'),
        ('UB', 'Upper Berth'),
        ('SL', 'Side Lower'),
        ('SU', 'Side Upper'),
    ]
    
    BOOKING_STATUS_CHOICES = [
        ('CONFIRMED', 'Confirmed'),
        ('RAC', 'Reservation Against Cancellation'),
        ('WL', 'Waitlist'),
    ]
    
    booking = models.ForeignKey(Booking, on_delete=models.CASCADE, related_name='passengers')
    name = models.CharField(max_length=100)
    age = models.IntegerField()
    gender = models.CharField(max_length=10, choices=GENDER_CHOICES)
    berth_preference = models.CharField(max_length=2, choices=BERTH_PREFERENCE_CHOICES)
    seat_number = models.CharField(max_length=10, blank=True, null=True)
    booking_status = models.CharField(max_length=20, choices=BOOKING_STATUS_CHOICES, default='CONFIRMED')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} - {self.booking.pnr_number}"

    class Meta:
        ordering = ['booking', 'name']
        verbose_name = 'Passenger'
        verbose_name_plural = 'Passengers'
