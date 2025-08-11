from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from exceptions.handlers import AlreadyExistsException
from utils.constants import (
    AlreadyExistsMessage, UserMessage, StationMessage, 
    RouteMessage, TrainMessage, PaymentMessage, BookingMessage)
from exceptions.handlers import (
    PermissionDeniedException, NotFoundException, InvalidInputException)
import logging

User = get_user_model()
logger = logging.getLogger("accounts")

class UserFieldValidators:
    """
    Reusable validation mixins for user-related fields.
    Eliminates code duplication in serializers.
    """
    
    @staticmethod
    def validate_email_uniqueness(value, context="registration", exclude_user=None):
        """
        Validates email uniqueness for user registration and updates.
        Only checks against active users, allowing registration with inactive
        user credentials.
        """
        queryset = User.objects
        if exclude_user:
            queryset = queryset.exclude(pk=exclude_user.pk)
            
        if queryset.filter(email=value, is_active=True).exists():
            logger.error(f"{context.title()} failed - Email already exists: {value}")
            raise AlreadyExistsException(AlreadyExistsMessage.EMAIL_ALREADY_EXISTS)
        
        return value
    
    @staticmethod
    def validate_mobile_number_uniqueness(value, context="registration", exclude_user=None):
        """
        Validates mobile number uniqueness for user registration and updates.
        Only checks against active users, allowing registration with inactive
        user credentials.
            
        Returns:
            str: The validated mobile number
            
        Raises:
            AlreadyExistsException: If mobile number already exists
        """
        queryset = User.objects
        if exclude_user:
            queryset = queryset.exclude(pk=exclude_user.pk)
            
        if queryset.filter(mobile_number=value, is_active=True).exists():
            logger.error(f"{context.title()} failed - Mobile number already exists: {value}")
            raise AlreadyExistsException(
                AlreadyExistsMessage.MOBILE_ALREADY_EXISTS
                )
        
        return value
    
    @staticmethod
    def validate_username_uniqueness(value, context="registration", exclude_user=None):
        """
        Validates username uniqueness for user registration and updates.
        Username must be unique across ALL users (active and inactive).
            
        Returns:
            str: The validated username
            
        Raises:
            AlreadyExistsException: If username already exists
        """
        queryset = User.objects
        if exclude_user:
            queryset = queryset.exclude(pk=exclude_user.pk)
            
        # Username must be unique across ALL users (active and inactive)
        if queryset.filter(username=value).exists():
            logger.error(f"{context.title()} failed - Username already exists: {value}")
            raise AlreadyExistsException(AlreadyExistsMessage.USERNAME_ALREADY_EXISTS)
        
        return value


class OTPValidator:
    """
    Reusable OTP validation logic.
    """
    
    @staticmethod
    def validate_otp(otp, expected_otp="123456", context="registration"):
        """
        Validates OTP for registration processes.
            
        Returns:
            bool: True if OTP is valid
            
        Raises:
            InvalidOTPException: If OTP is invalid
        """
        
        if otp != expected_otp:
            logger.error(f"Invalid OTP provided for {context} - OTP: {otp}")
            raise PermissionDeniedException(UserMessage.INVALID_OTP)
        return True 
    

class StationValidators:
    """
    Centralized validation logic for station-related operations.
    Eliminates code duplication across views and models.
    """
    
    @staticmethod
    def validate_station_code(code, exclude_pk=None):
        """
        Validates station code format and uniqueness.
        
        Args:
            code (str): Station code to validate
            exclude_pk (int, optional): PK to exclude from uniqueness check
            
        Returns:
            str: Validated and normalized station code
            
        Raises:
            ValidationError: If code format is invalid
            AlreadyExistsException: If code already exists
        """
        if not code:
            raise ValidationError(StationMessage.STATION_CODE_REQUIRED)
        
        # Format validation
        if not (2 <= len(code) <= 5):
            raise ValidationError(StationMessage.STATION_CODE_INVALID)
        
        # Normalize to uppercase
        code = code.upper()
        from stations.models import Station
        
        queryset = Station.all_objects
        if exclude_pk:
            queryset = queryset.exclude(pk=exclude_pk)
            
        if queryset.filter(code__iexact=code).exists():
            logger.error(f"Station code already exists: {code}")
            raise AlreadyExistsException(StationMessage.STATION_ALREADY_EXISTS)
        
        return code
    
    @staticmethod
    def validate_station_name(name, exclude_pk=None):
        """
        Validates station name format and uniqueness.
        
        Args:
            name (str): Station name to validate
            exclude_pk (int, optional): PK to exclude from uniqueness check
            
        Returns:
            str: Validated station name
            
        Raises:
            ValidationError: If name format is invalid
            AlreadyExistsException: If name already exists
        """
        if not name:
            raise ValidationError(StationMessage.STATION_NAME_REQUIRED)
        
        # Format validation
        if len(name.strip()) < 3:
            raise ValidationError(StationMessage.STATION_NAME_TOO_SHORT)
        
        name = name.strip()
        from stations.models import Station
        # Uniqueness validation
        queryset = Station.all_objects
        if exclude_pk:
            queryset = queryset.exclude(pk=exclude_pk)
            
        if queryset.filter(name__iexact=name).exists():
            logger.error(f"Station name already exists: {name}")
            raise AlreadyExistsException(StationMessage.STATION_ALREADY_EXISTS)
        
        return name
    
    @staticmethod
    def validate_station_active_for_operation(station, operation="access"):
        """
        Validates that a station is active for a specific operation.
        
        Args:
            station (Station): Station object to validate
            operation (str): Operation being performed (for logging)
            
        Raises:
            NotFoundException: If station is inactive
        """
        if not getattr(station, "is_active", False):
            logger.warning(f"Station {station.name} ({station.code}) is inactive; cannot {operation}.")
            raise NotFoundException(StationMessage.STATION_NOT_FOUND)
    
    @staticmethod
    def validate_station_master_assignment(user_id, station):
        """
        Validates station master assignment with comprehensive checks.
        
        Args:
            user_id (int): User ID to assign as station master
            station (Station): Station to assign master to
            
        Returns:
            User: Validated user object
            
        Raises:
            NotFoundException: If user not found or not eligible
            AlreadyExistsException: If assignment conflicts exist
        """
        # Single query with all validation checks
        try:
            user = User.objects.select_related('station').get(
                id=user_id, 
                is_active=True, 
                role="station_master"
            )
        except User.DoesNotExist:
            logger.warning(f"User {user_id} not found or not eligible as station master.")
            raise NotFoundException(UserMessage.MASTER_NOT_FOUND)
        
        # Check if user is already assigned to another station
        if hasattr(user, "station") and user.station is not None and user.station != station:
            logger.warning(
                f"User {user.username} (ID: {user.id}) is already assigned as station master to station {user.station.name} ({user.station.code})."
            )
            raise AlreadyExistsException(UserMessage.MASTER_ALREADY_ASSIGNED)
        
        # Check if station already has a different master
        if station.station_master and station.station_master != user:
            logger.warning(
                f"Station {station.name} ({station.code}) already has a different station master ({station.station_master.username})."
            )
            raise AlreadyExistsException(UserMessage.STATION_MASTER_EXISTS)
        
        return user
    
    @staticmethod
    def validate_station_for_deletion(station):
        """
        Validates that a station can be safely deleted.
        
        Args:
            station (Station): Station to validate for deletion
            
        Raises:
            NotFoundException: If station is already inactive
        """
        if not station.is_active:
            logger.warning(f"Station {station.name} ({station.code}) is already inactive.")
            raise NotFoundException(StationMessage.STATION_NOT_FOUND)
    
    @staticmethod
    def validate_station_exists(code):
        """
        Validates that a station exists and is retrievable.
        
        Args:
            code (str): Station code to validate
            
        Returns:
            Station: Station object if found
            
        Raises:
            NotFoundException: If station not found
        """
        try:
            from stations.models import Station
            station = Station.all_objects.select_related('station_master').get(code=code.upper())
            return station
        except Station.DoesNotExist:
            logger.warning(f"Station with code {code} not found.")
            raise NotFoundException(StationMessage.STATION_NOT_FOUND)


class RouteValidators:
    """
    Centralized validation logic for route-related operations.
    Only contains methods used 2+ times to reduce redundancy.
    """
    
    @staticmethod
    def validate_station_pair(from_code, to_code):
        """
        Validates a pair of station codes and returns station objects.
        Single database query for both stations to reduce hits.
        
        Args:
            from_code (str): From station code
            to_code (str): To station code
            
        Returns:
            tuple: (from_station, to_station) Station objects
            
        Raises:
            InvalidInputException: If stations are the same
            NotFoundException: If stations not found
        """
        if from_code == to_code:
            raise InvalidInputException(RouteMessage.ROUTE_EDGE_FROM_AND_TO_SAME)
        
        # Single query to get both stations
        from stations.models import Station
        stations = Station.objects.filter(code__in=[from_code, to_code])
        station_map = {station.code: station for station in stations}
        
        if from_code not in station_map or to_code not in station_map:
            missing_codes = []
            if from_code not in station_map:
                missing_codes.append(from_code)
            if to_code not in station_map:
                missing_codes.append(to_code)
            logger.error(f"Stations not found: {missing_codes}")
            raise NotFoundException(RouteMessage.ROUTE_EDGE_STATION_NOT_FOUND)
        
        return station_map[from_code], station_map[to_code]
    
    @staticmethod
    def validate_distance(distance):
        """
        Validates distance is a positive integer.
        
        Args:
            distance: Distance value to validate
            
        Returns:
            int: Validated distance
            
        Raises:
            InvalidInputException: If distance is invalid
        """
        try:
            distance = int(distance)
        except (TypeError, ValueError):
            raise InvalidInputException(RouteMessage.ROUTE_EDGE_INVALID_DISTANCE)
        
        if distance <= 0:
            raise InvalidInputException(RouteMessage.ROUTE_EDGE_INVALID_DISTANCE)
        
        return distance
    
    @staticmethod
    def validate_edge_exists(from_station, to_station, is_bidirectional=True, include_inactive=False):
        """
        Validates if a route edge already exists between stations.
        Optimized to use single query for bidirectional checks.
        
        Args:
            from_station (Station): From station object
            to_station (Station): To station object
            is_bidirectional (bool): Whether to check bidirectional edges
            include_inactive (bool): Whether to include inactive edges
            
        Returns:
            bool: True if edge exists
            
        Raises:
            AlreadyExistsException: If edge already exists
        """
        from routes.models import RouteEdge
        
        queryset = RouteEdge.objects
        if not include_inactive:
            queryset = queryset.filter(is_active=True)
        
        if is_bidirectional:
            # Single query with Q objects for bidirectional check
            from django.db.models import Q
            exists = queryset.filter(
                Q(from_station=from_station, to_station=to_station, is_bidirectional=True) |
                Q(from_station=to_station, to_station=from_station, is_bidirectional=True)
            ).exists()
            
            if exists:
                raise AlreadyExistsException(RouteMessage.ROUTE_EDGE_ALREADY_EXISTS)
        else:
            exists = queryset.filter(
                from_station=from_station,
                to_station=to_station,
                is_bidirectional=False
            ).exists()
            
            if exists:
                raise AlreadyExistsException(RouteMessage.ROUTE_EDGE_UNIDIRECTIONAL_EXISTS)
        
        return False


class TrainValidators:
    """
    Reusable validation logic for train operations.
    Centralizes train-related validations to reduce redundancy.
    """
    
    @staticmethod
    def validate_train_number_uniqueness(train_number, exclude_pk=None):
        """
        Validates that train number is unique among all trains.
        
        Args:
            train_number (str): The train number to validate
            exclude_pk (int, optional): PK to exclude from validation (for updates)
            
        Returns:
            str: The validated train number
            
        Raises:
            AlreadyExistsException: If train number already exists
        """
        from trains.models import Train
        
        queryset = Train.all_objects.filter(train_number=train_number)
        if exclude_pk:
            queryset = queryset.exclude(pk=exclude_pk)
        if queryset.exists():
            logger.error(f"Train number already exists: {train_number}")
            raise AlreadyExistsException(TrainMessage.TRAIN_ALREADY_EXISTS)
        return train_number
    
    @staticmethod
    def validate_schedule_uniqueness(train, start_time, direction, exclude_pk=None):
        """
        Validates that train schedule is unique for given train, time, and direction.
        
        Args:
            train: Train instance
            start_time: Start time of schedule
            direction (str): Direction of schedule
            exclude_pk (int, optional): PK to exclude from validation (for updates)
            
        Returns:
            bool: True if validation passes
            
        Raises:
            AlreadyExistsException: If schedule already exists
        """
        from trains.models import TrainSchedule
        
        qs = TrainSchedule.objects.filter(
            train=train, start_time=start_time, direction=direction, is_active=True
        )
        if exclude_pk:
            qs = qs.exclude(pk=exclude_pk)
        if qs.exists():
            raise AlreadyExistsException(TrainMessage.SCHEDULE_ALREADY_EXISTS)
        return True
    
    @staticmethod
    def validate_stations_exist(stop_codes):
        """
        Validates that all station codes exist and returns station objects.
        Optimized to use single query instead of multiple individual queries.
        
        Args:
            stop_codes (list): List of station codes to validate
            
        Returns:
            list: List of station objects
            
        Raises:
            RouteStopsNotFoundException: If any station is not found
        """
        from stations.models import Station
        
        # Single query to get all stations
        stations = list(Station.objects.filter(code__in=[code.upper() for code in stop_codes]))
        
        if len(stations) != len(stop_codes):
            found_codes = {station.code.upper() for station in stations}
            missing_codes = [code.upper() for code in stop_codes if code.upper() not in found_codes]
            logger.error(f"Stations not found: {missing_codes}")
            raise NotFoundException(StationMessage.STATION_NOT_FOUND)
        
        return stations


class PaymentValidators:
    """
    Reusable validation logic for payment operations.
    Centralizes payment-related validations to reduce redundancy.
    """
    
    @staticmethod
    def validate_payment_method(value):
        """
        Validates that the payment method is UPI or WALLET.
        
        Args:
            value (str): Payment method to validate
            
        Returns:
            str: Validated payment method
            
        Raises:
            InvalidInputException: If payment method is invalid
        """
        allowed_methods = ["UPI", "WALLET"]
        if value not in allowed_methods:
            raise InvalidInputException(PaymentMessage.INVALID_PAYMENT_METHOD)
        return value
    
    @staticmethod
    def validate_payment_amount(value):
        """
        Validates that the payment amount is positive.
        
        Args:
            value: Amount to validate
            
        Returns:
            float: Validated amount
            
        Raises:
            InvalidInputException: If amount is invalid
        """
        if value <= 0:
            raise InvalidInputException(PaymentMessage.PAYMENT_AMOUNT_ZERO)
        return value
    
    @staticmethod
    def validate_transaction_id(value):
        """
        Validates that the transaction ID is not blank.
        
        Args:
            value (str): Transaction ID to validate
            
        Returns:
            str: Validated transaction ID
            
        Raises:
            InvalidInputException: If transaction ID is blank
        """
        if not value or not value.strip():
            raise InvalidInputException(PaymentMessage.PAYMENT_TRANSACTION_ID_BLANK)
        return value
    
    @staticmethod
    def validate_payment_status(value):
        """
        Validates that the status is SUCCESS or FAILED.
        
        Args:
            value (str): Status to validate
            
        Returns:
            str: Validated status
            
        Raises:
            InvalidInputException: If status is invalid
        """
        allowed_statuses = ["SUCCESS", "FAILED"]
        if value not in allowed_statuses:
            raise InvalidInputException(PaymentMessage.PAYMENT_STATUS_INVALID)
        return value
    
    @staticmethod
    def validate_user_authorized(user):
        """
        Validates that user is not staff or superuser.
        
        Args:
            user: User object to validate
            
        Raises:
            PermissionDeniedException: If user is staff or superuser
        """
        if getattr(user, "is_staff", False) or getattr(user, "is_superuser", False):
            logger.warning(f"Admin/staff {user} attempted to make a payment.")
            raise PermissionDeniedException(PaymentMessage.PAYMENT_UNAUTHORIZED)
    
    @staticmethod
    def validate_booking_for_payment(booking_id, user):
        """
        Validates that booking exists and is in PENDING status.
        Optimized to use single query with select_related.
        
        Args:
            booking_id: Booking ID to validate
            user: User object
            
        Returns:
            Booking: Validated booking object
            
        Raises:
            NotFoundException: If booking not found or not in PENDING status
        """
        from bookingsystem.models import Booking
        
        try:
            booking = Booking.objects.select_related('user').get(id=booking_id, user=user)
            if getattr(booking, "booking_status", None) != "PENDING":
                logger.warning(f"Booking {booking_id} not found for payment.")
                raise NotFoundException(PaymentMessage.PAYMENT_NOT_FOUND)
            return booking
        except Booking.DoesNotExist:
            logger.warning(f"Booking {booking_id} not found for user {user}")
            raise NotFoundException(PaymentMessage.PAYMENT_NOT_FOUND)
    
    @staticmethod
    def validate_payment_amount_matches_booking(amount, booking):
        """
        Validates that payment amount matches booking fare.
        
        Args:
            amount: Payment amount
            booking: Booking object
            
        Raises:
            InvalidInputException: If amounts don't match
        """
        if float(amount) != float(getattr(booking, "total_fare", 0)):
            logger.warning(
                f"Payment amount does not match booking fare for booking {booking.id}"
            )
            raise InvalidInputException(PaymentMessage.PAYMENT_FAILED)
    
    @staticmethod
    def check_existing_successful_payment(booking):
        """
        Checks if a successful payment already exists for the booking.
        
        Args:
            booking: Booking object
            
        Raises:
            AlreadyExistsException: If successful payment already exists
        """
        from payment.models import PaymentTransaction
        
        if PaymentTransaction.objects.filter(booking=booking, status="SUCCESS").exists():
            logger.warning(f"Payment already completed for booking {booking.id}")
            raise AlreadyExistsException(PaymentMessage.PAYMENT_ALREADY_SUCCESS)


class BookingValidators:
    """
    Reusable validation logic for booking operations.
    Centralizes booking-related validations to reduce redundancy.
    """
    
    @staticmethod
    def validate_station_pair(from_code, to_code):
        """
        Validates a pair of station codes and returns station objects.
        Optimized to use single query instead of multiple individual queries.
        
        Args:
            from_code (str): From station code
            to_code (str): To station code
            
        Returns:
            tuple: (from_station, to_station) Station objects
            
        Raises:
            InvalidInputException: If stations are the same
            NotFoundException: If stations not found
        """
        if from_code == to_code:
            raise InvalidInputException(BookingMessage.FROM_AND_TO_MUST_BE_DIFFERENT)
        
        # Single query to get both stations
        from stations.models import Station
        stations = Station.objects.filter(code__in=[from_code.upper(), to_code.upper()])
        station_map = {station.code.upper(): station for station in stations}
        
        if from_code.upper() not in station_map or to_code.upper() not in station_map:
            missing_codes = []
            if from_code.upper() not in station_map:
                missing_codes.append(from_code.upper())
            if to_code.upper() not in station_map:
                missing_codes.append(to_code.upper())
            logger.error(f"Stations not found: {missing_codes}")
            raise NotFoundException(StationMessage.STATION_NOT_FOUND)
        
        return station_map[from_code.upper()], station_map[to_code.upper()]
    
    @staticmethod
    def validate_class_type(class_type):
        """
        Validates that class type is valid.
        
        Args:
            class_type (str): Class type to validate
            
        Returns:
            str: Validated class type
            
        Raises:
            InvalidInputException: If class type is invalid
        """
        valid_classes = ["GENERAL", "FC"]
        if class_type.upper() not in valid_classes:
            raise InvalidInputException(BookingMessage.INVALID_CLASS_TYPE)
        return class_type.upper()
    
    @staticmethod
    def validate_user_authorized(user):
        """
        Validates that user is not staff or superuser for booking creation.
        
        Args:
            user: User object to validate
            
        Raises:
            PermissionDeniedException: If user is staff or superuser
        """
        if getattr(user, "is_staff", False) or getattr(user, "is_superuser", False):
            logger.warning(f"Admin/staff {user} attempted to create a booking.")
            raise PermissionDeniedException(BookingMessage.ADMIN_CANNOT_CREATE_BOOKING)
    
    @staticmethod
    def validate_booking_for_exchange(booking):
        """
        Validates that booking can be exchanged.
        
        Args:
            booking: Booking object to validate
            
        Raises:
            InvalidInputException: If booking cannot be exchanged
        """
        if booking.booking_status != "BOOKED":
            raise InvalidInputException(BookingMessage.BOOKED_TICKETS_CAN_BE_EXCHANGED)
    
    @staticmethod
    def validate_exchange_destination(booking, new_to_station):
        """
        Validates that new destination is different from current and source.
        
        Args:
            booking: Booking object
            new_to_station: New destination station
            
        Raises:
            InvalidInputException: If destination is invalid
        """
        if booking.to_station == new_to_station:
            raise InvalidInputException(BookingMessage.FROM_AND_TO_MUST_BE_DIFFERENT)
        
        if booking.from_station == new_to_station:
            raise InvalidInputException(BookingMessage.FROM_AND_TO_MUST_BE_DIFFERENT)