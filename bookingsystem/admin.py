from django.contrib import admin
from .models import Booking, Passenger

class PassengerInline(admin.TabularInline):
    model = Passenger
    extra = 0
    readonly_fields = ['created_at']

@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = ['pnr_number', 'user', 'train', 'source_station', 'destination_station', 
                   'travel_date', 'booking_status', 'class_type', 'quota', 'total_fare', 'created_at']
    list_filter = ['booking_status', 'class_type', 'quota', 'travel_date', 'created_at']
    search_fields = ['pnr_number', 'user__username', 'train__train_number', 'train__name']
    readonly_fields = ['pnr_number', 'created_at', 'updated_at']
    inlines = [PassengerInline]
    ordering = ['-created_at']

@admin.register(Passenger)
class PassengerAdmin(admin.ModelAdmin):
    list_display = ['name', 'booking', 'age', 'gender', 'berth_preference', 'seat_number', 'booking_status']
    list_filter = ['gender', 'berth_preference', 'booking_status', 'created_at']
    search_fields = ['name', 'booking__pnr_number']
    readonly_fields = ['created_at']
    ordering = ['booking', 'name']
