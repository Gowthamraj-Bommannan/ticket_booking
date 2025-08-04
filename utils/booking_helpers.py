import random
import string
import logging
from django.utils import timezone
from django.db.models import Count, Q
from datetime import timedelta

logger = logging.getLogger("booking")


class BookingHelpers:
    """
    Reusable helper methods for booking operations.
    Centralizes booking-related utilities to reduce redundancy.
    """
    
    @staticmethod
    def generate_unique_ticket_number():
        """
        Generate a unique 8-digit ticket number.
        Optimized to reduce database hits.
        
        Returns:
            str: Unique ticket number
        """
        from bookingsystem.models import Booking
        
        while True:
            number = "".join(random.choices(string.digits, k=8))
            if not Booking.objects.filter(ticket_number=number).exists():
                return number
    
    @staticmethod
    def calculate_fare(class_type, num_passengers):
        """
        Calculate fare for local train booking.
        
        Args:
            class_type (str): Class type (GENERAL/FC)
            num_passengers (int): Number of passengers
            
        Returns:
            float: Calculated fare
        """
        base_rate = 10
        multiplier = 2 if class_type.upper() == "FC" else 1
        return base_rate * multiplier * num_passengers
    
    @staticmethod
    def get_booking_statistics_optimized(queryset):
        """
        Get booking statistics with optimized single query.
        Reduces multiple count queries to single aggregation.
        
        Args:
            queryset: Booking queryset
            
        Returns:
            dict: Booking statistics
        """
        stats = queryset.aggregate(
            total=Count('id'),
            pending=Count('id', filter=Q(booking_status="PENDING")),
            booked=Count('id', filter=Q(booking_status="BOOKED")),
            failed=Count('id', filter=Q(booking_status="FAILED"))
        )
        
        return {
            "total_bookings": stats['total'],
            "pending_bookings": stats['pending'],
            "booked_tickets": stats['booked'],
            "failed_bookings": stats['failed'],
        }
    
    @staticmethod
    def check_train_availability_optimized(from_station, to_station, travel_date, class_type):
        """
        Check if trains are available for the given route and date.
        Optimized to use single query with select_related.
        
        Args:
            from_station: From station object
            to_station: To station object
            travel_date: Travel date
            class_type (str): Class type
            
        Returns:
            list: Available trains with schedules
        """
        from trains.models import Train, TrainSchedule
        
        day_of_week = travel_date.weekday()
        day_codes = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
        day_code = day_codes[day_of_week]
        
        valid_classes = ["GENERAL", "FC"]
        if class_type.upper() not in valid_classes:
            return []
        
        # Single optimized query with select_related
        schedules = TrainSchedule.objects.filter(
            train__is_active=True,
            is_active=True,
            days_of_week__icontains=day_code
        ).select_related('train', 'route_template')
        
        available_trains = []
        from_code = from_station.code.upper()
        to_code = to_station.code.upper()
        
        for schedule in schedules:
            stops = [stop.strip().upper() for stop in schedule.route_template.stops]
            
            if from_code in stops and to_code in stops:
                from_index = stops.index(from_code)
                to_index = stops.index(to_code)
                
                if from_index < to_index:
                    segment_stops_with_time = schedule.stops_with_time[
                        from_index : to_index + 1
                    ]
                    
                    available_trains.append({
                        "train_number": schedule.train.train_number,
                        "train_name": schedule.train.name,
                        "schedule_id": schedule.id,
                        "departure_date": travel_date,
                        "departure_time": (
                            segment_stops_with_time[0]["departure_time"]
                            if segment_stops_with_time
                            else schedule.start_time
                        ),
                        "class_type": class_type,
                        "route_stops": stops,
                        "from_station": from_station.name,
                        "to_station": to_station.name,
                        "stops_with_time": segment_stops_with_time,
                    })
        
        return available_trains
    
    @staticmethod
    def get_next_available_trains_optimized(from_station, to_station, class_type, limit=5):
        """
        Get the next available trains for the given route.
        Optimized to reduce database hits.
        
        Args:
            from_station: From station object
            to_station: To station object
            class_type (str): Class type
            limit (int): Maximum number of trains to return
            
        Returns:
            list: Available trains sorted by departure time
        """
        today = timezone.now().date()
        available_trains = []
        
        for day_offset in range(7):  # Check next 7 days
            check_date = today + timedelta(days=day_offset)
            trains = BookingHelpers.check_train_availability_optimized(
                from_station, to_station, check_date, class_type
            )
            available_trains.extend(trains)
        
        # Sort by departure date and time
        available_trains.sort(key=lambda x: (x["departure_date"], x["departure_time"]))
        return available_trains[:limit]
    
    @staticmethod
    def validate_booking_request_optimized(from_station, to_station, class_type):
        """
        Validate if a booking request is possible.
        Optimized to use centralized validators.
        
        Args:
            from_station: From station object
            to_station: To station object
            class_type (str): Class type
            
        Returns:
            tuple: (is_valid, error_message, available_trains)
        """
        from utils.validators import BookingValidators
        
        if not from_station or not to_station:
            return False, "Source and destination stations are required.", []
        
        if from_station == to_station:
            return False, "Source and destination stations must be different.", []
        
        # Use centralized validator
        try:
            BookingValidators.validate_class_type(class_type)
        except Exception as e:
            return False, str(e), []
        
        available_trains = BookingHelpers.get_next_available_trains_optimized(
            from_station, to_station, class_type
        )
        
        if not available_trains:
            return False, "No trains found between the given stations.", []
        
        return True, "Booking request is valid.", available_trains 