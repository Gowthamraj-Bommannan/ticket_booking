import random, string
from bookingsystem.models import Booking, Passenger
from trains.models import TrainClass

def get_booked_seats(train_id, class_type, travel_date, segment):
    """
    Return all seat_numbers already assigned on overlapping bookings for the given segment.
    Segment: (source_station, destination_station)
    """
    source, dest = segment
    # Get all bookings for this train/class/date that overlap the segment
    bookings = Booking.objects.filter(
        train_id=train_id,
        class_type=class_type,
        travel_date=travel_date,
        booking_status__in=['CONFIRMED', 'RAC']
    )
    booked_seats = set()
    for booking in bookings:
        b_source = booking.source_station
        b_dest = booking.destination_station
        # Overlap if not (A ends before B starts or A starts after B ends)
        if not (b_dest.sequence <= source.sequence or b_source.sequence >= dest.sequence):
            for p in booking.passengers.all():
                if p.seat_number:
                    booked_seats.add(p.seat_number)
    return booked_seats

def assign_seats(booking):
    """
    Assign seats to passengers in a booking based on availability, quota, and preferences.
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
    available_seats = [f"{class_type[0]}{i+1:03d}" for i in range(total_seats) if f"{class_type[0]}{i+1:03d}" not in booked_seats]
    # Assign seats to passengers
    for i, passenger in enumerate(booking.passengers.all()):
        if i < len(available_seats):
            passenger.seat_number = available_seats[i]
            passenger.booking_status = 'CONFIRMED'
        else:
            passenger.seat_number = None
            passenger.booking_status = 'RAC' if i < len(available_seats) + 10 else 'WL'
        passenger.save()

def generate_unique_pnr():
    """Generate a unique 10-digit alphanumeric PNR number."""
    from bookingsystem.models import Booking
    while True:
        pnr = ''.join(random.choices(string.ascii_uppercase + string.digits, k=10))
        if not Booking.objects.filter(pnr_number=pnr).exists():
            return pnr
