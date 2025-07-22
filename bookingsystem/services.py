import random, string
from bookingsystem.models import Booking
from trains.models import Train, TrainSchedule
from django.utils import timezone
import logging

logger = logging.getLogger("booking_debug")

def generate_unique_ticket_number():
    """Generate a unique 8-digit ticket number."""
    while True:
        number = ''.join(random.choices(string.digits, k=8))
        if not Booking.objects.filter(ticket_number=number).exists():
            return number

def calculate_fare(class_type, num_passengers):
    """Calculate fare for local train booking."""
    base_rate = 10
    multiplier = 2 if class_type.upper() == 'FC' else 1
    return base_rate * multiplier * num_passengers

def cancel_booking(booking):
    """Cancel a local train booking."""
    if booking.booking_status == 'FAILED':
        return False, "Booking is already cancelled."
    
    booking.booking_status = 'FAILED'
    booking.save()
    return True, "Booking cancelled successfully."

def get_booking_statistics(user):
    """Get booking statistics for a user."""
    total_bookings = Booking.objects.filter(user=user).count()
    successful_bookings = Booking.objects.filter(user=user, booking_status='BOOKED').count()
    failed_bookings = Booking.objects.filter(user=user, booking_status='FAILED').count()
    
    return {
        'total_bookings': total_bookings,
        'successful_bookings': successful_bookings,
        'failed_bookings': failed_bookings,
        'success_rate': (successful_bookings / total_bookings * 100) if total_bookings > 0 else 0
    }

def check_train_availability(from_station, to_station, travel_date, class_type):
    """
    Check if trains are available for the given route and date.
    Returns available trains with their schedules.
    """
    day_of_week = travel_date.weekday()
    day_codes = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
    day_code = day_codes[day_of_week]
    valid_classes = ['GENERAL', 'FC']
    if class_type.upper() not in valid_classes:
        return []
    trains = Train.objects.filter(is_active=True)
    available_trains = []
    for train in trains:
        # All trains are available for both classes
        schedules = TrainSchedule.objects.filter(
            train=train,
            is_active=True,
            days_of_week__icontains=day_code
        )
        for schedule in schedules:
            stops = [stop.strip().upper() for stop in schedule.route_template.stops]
            from_code = from_station.code.upper()
            to_code = to_station.code.upper()
            if from_code in stops and to_code in stops:
                from_index = stops.index(from_code)
                to_index = stops.index(to_code)
                if from_index < to_index:
                    segment_stops_with_time = schedule.stops_with_time[from_index:to_index+1]
                    available_trains.append({
                        'train_number': train.train_number,
                        'train_name': train.name,
                        'schedule_id': schedule.id,
                        'departure_date': travel_date,
                        'departure_time': segment_stops_with_time[0]['departure_time'] if segment_stops_with_time else schedule.start_time,
                        'class_type': class_type,
                        'route_stops': stops,
                        'from_station': from_station.name,
                        'to_station': to_station.name,
                        'stops_with_time': segment_stops_with_time
                    })
    return available_trains

def get_next_available_trains(from_station, to_station, class_type, limit=5):
    """
    Get the next available trains for the given route.
    Returns trains sorted by departure time.
    """
    today = timezone.now().date()
    available_trains = []
    for day_offset in range(7):  # Check next 7 days
        check_date = today + timezone.timedelta(days=day_offset)
        trains = check_train_availability(from_station, to_station, check_date, class_type)
        for train_info in trains:
            available_trains.append(train_info)
    available_trains.sort(key=lambda x: (x['departure_date'], x['departure_time']))
    return available_trains[:limit]

def validate_booking_request(from_station, to_station, class_type):
    """
    Validate if a booking request is possible.
    Returns (is_valid, error_message, available_trains)
    """
    if not from_station or not to_station:
        return False, "Source and destination stations are required.", []
    if from_station == to_station:
        return False, "Source and destination stations must be different.", []
    valid_classes = ['GENERAL', 'FC']
    if class_type.upper() not in valid_classes:
        return False, f"Invalid class type. Must be one of: {', '.join(valid_classes)}", []
    available_trains = get_next_available_trains(from_station, to_station, class_type)
    if not available_trains:
        return False, "No trains found between the given stations.", []
    return True, "Booking request is valid.", available_trains 