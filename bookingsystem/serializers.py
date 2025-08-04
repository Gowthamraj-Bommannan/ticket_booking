from rest_framework import serializers
from .models import Booking
from utils.validators import BookingValidators
from utils.booking_helpers import BookingHelpers
from exceptions.handlers import (
    InvalidInputException, NotFoundException
    )
from utils.constants import BookingMessage, StationMessage


class BookingSerializer(serializers.ModelSerializer):
    """
    Serializes booking data for API usage.
    Handles validation and representation using centralized validators.
    """

    from_station_code = serializers.CharField(write_only=True)
    to_station_code = serializers.CharField(write_only=True)
    from_station = serializers.CharField(source="from_station.code",
                                         read_only=True)
    to_station = serializers.CharField(source="to_station.code",
                                       read_only=True)

    class Meta:
        model = Booking
        fields = [
            "id",
            "user",
            "from_station_code",
            "to_station_code",
            "from_station",
            "to_station",
            "class_type",
            "num_of_passenegers",
            "total_fare",
            "booking_time",
            "expiry_time",
            "travel_date",
            "ticket_number",
            "booking_status",
        ]
        read_only_fields = [
            "id",
            "user",
            "from_station",
            "to_station",
            "total_fare",
            "booking_time",
            "travel_date",
            "ticket_number",
            "booking_status",
            "created_at",
            "updated_at",
            "expiry_time",
        ]

    def validate(self, data):
        """
        Validates booking request data using centralized validators.
        Checks for duplicate stations, invalid class type, and station existence.
        """
        from_code = data.get("from_station_code", "").strip().upper()
        to_code = data.get("to_station_code", "").strip().upper()
        class_type = data.get("class_type", "GENERAL")
        
        # Use centralized validators
        from_station, to_station = BookingValidators.validate_station_pair(from_code, to_code)
        BookingValidators.validate_class_type(class_type)
        
        # Use optimized booking request validation
        is_valid, error_message, available_trains = BookingHelpers.validate_booking_request_optimized(
            from_station, to_station, class_type
        )
        
        if not is_valid:
            raise serializers.ValidationError(error_message)
        
        return data
