from decimal import Decimal
import random, string
from bookingsystem.models import Booking, Passenger
from trains.models import TrainClass
from routes.models import TrainRouteStop
from django.db.models import Q

def get_booked_seats(train_id, class_type, travel_date, segment):
    """
    Return all seat_numbers already assigned on overlapping bookings for the given segment.
    Segment: (source_station, destination_station)
    """
    source_station, dest_station = segment
    source_stop = TrainRouteStop.objects.filter(train_id=train_id, station=source_station).first()
    dest_stop = TrainRouteStop.objects.filter(train_id=train_id, station=dest_station).first()
    if not source_stop or not dest_stop:
        return set()  # No route info, so no seats booked
    bookings = Booking.objects.filter(
        train_id=train_id,
        class_type=class_type,
        travel_date=travel_date,
        booking_status__in=['CONFIRMED', 'RAC']
    )
    booked_seats = set()
    for booking in bookings:
        b_source_stop = TrainRouteStop.objects.filter(train_id=train_id, station=booking.source_station).first()
        b_dest_stop = TrainRouteStop.objects.filter(train_id=train_id, station=booking.destination_station).first()
        if not b_source_stop or not b_dest_stop:
            continue
        # Overlap if not (A ends before B starts or A starts after B ends)
        if not (b_dest_stop.sequence <= source_stop.sequence or b_source_stop.sequence >= dest_stop.sequence):
            for p in booking.passengers.all():
                if p.seat_number:
                    booked_seats.add(p.seat_number)
    return booked_seats

def assign_seats(booking):
    """
    Assign seats to passengers in a booking based on availability, quota, and preferences.
    Honors berth preference (lower for elderly >60), assigns berth_type, and ensures no duplicate seat numbers.
    """
    train = booking.train
    class_type = booking.class_type
    travel_date = booking.travel_date
    source = booking.source_station
    dest = booking.destination_station
    segment = (source, dest)
    try:
        train_class = TrainClass.objects.get(train=train, class_type=class_type)
        total_seats = train_class.seat_capacity
    except TrainClass.DoesNotExist:
        total_seats = 0
    booked_seats = get_booked_seats(train.id, class_type, travel_date, segment)
    # Berth types for assignment
    berth_types = ['LB', 'MB', 'UB', 'SL', 'SU']
    available_seats = [f"{class_type[0]}{i+1:03d}" for i in range(total_seats) if f"{class_type[0]}{i+1:03d}" not in booked_seats]
    available_berths = berth_types * (total_seats // len(berth_types) + 1)
    assigned = set()
    # Elderly first pass
    elderly = [p for p in booking.passengers.all() if p.age >= 60 and p.berth_preference == 'LB']
    others = [p for p in booking.passengers.all() if p not in elderly]
    idx = 0
    for passenger in elderly:
        # Assign lower berth if available
        if idx < len(available_seats):
            passenger.seat_number = available_seats[idx]
            passenger.berth_type = 'LB'
            passenger.booking_status = 'CONFIRMED'
            assigned.add(passenger.seat_number)
            idx += 1
        else:
            passenger.seat_number = None
            passenger.berth_type = None
            passenger.booking_status = 'RAC' if idx < len(available_seats) + 10 else 'WL'
        passenger.save()
    # Others
    for passenger in others:
        if idx < len(available_seats):
            passenger.seat_number = available_seats[idx]
            passenger.berth_type = passenger.berth_preference if passenger.berth_preference in berth_types else available_berths[idx % len(berth_types)]
            passenger.booking_status = 'CONFIRMED'
            assigned.add(passenger.seat_number)
            idx += 1
        else:
            passenger.seat_number = None
            passenger.berth_type = None
            passenger.booking_status = 'RAC' if idx < len(available_seats) + 10 else 'WL'
        passenger.save()

def release_seats_and_promote(booking):
    """
    On cancellation, release seats and auto-promote RAC/WL for the same train/date/class.
    """
    # Release seats for cancelled booking
    for p in booking.passengers.all():
        p.seat_number = None
        p.berth_type = None
        p.booking_status = 'CANCELLED'
        p.save()
    # Promote RAC/WL for this train/date/class
    train = booking.train
    class_type = booking.class_type
    travel_date = booking.travel_date
    # Get all bookings in RAC/WL order
    rac_bookings = Booking.objects.filter(
        train=train, class_type=class_type, travel_date=travel_date, booking_status='RAC'
    ).order_by('created_at')
    wl_bookings = Booking.objects.filter(
        train=train, class_type=class_type, travel_date=travel_date, booking_status='WL'
    ).order_by('created_at')
    # Try to promote RAC to CONFIRMED, WL to RAC
    for rac_booking in rac_bookings:
        assign_seats(rac_booking)
        rac_booking.save()
    for wl_booking in wl_bookings:
        assign_seats(wl_booking)
        wl_booking.save()

def generate_unique_pnr():
    """Generate a unique 10-digit alphanumeric PNR number."""
    from bookingsystem.models import Booking
    while True:
        pnr = ''.join(random.choices(string.ascii_uppercase + string.digits, k=10))
        if not Booking.objects.filter(pnr_number=pnr).exists():
            return pnr 