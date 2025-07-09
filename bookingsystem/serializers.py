from rest_framework import serializers
from django.db.models import Q, Count
from django.utils import timezone
from datetime import datetime, timedelta
from decimal import Decimal
from .models import Booking, Passenger
from trains.models import Train, TrainClass
from stations.models import Station
from routes.models import TrainRouteStop

class PassengerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Passenger
        fields = ['id', 'name', 'age', 'gender', 'berth_preference', 'seat_number', 'booking_status', 'created_at']
        read_only_fields = ['id', 'seat_number', 'booking_status', 'created_at']

    def validate_age(self, value):
        if value < 1 or value > 120:
            raise serializers.ValidationError("Age must be between 1 and 120 years.")
        return value

class BookingSerializer(serializers.ModelSerializer):
    passengers = PassengerSerializer(many=True, read_only=True)
    train_number = serializers.CharField(source='train.train_number', read_only=True)
    train_name = serializers.CharField(source='train.name', read_only=True)
    source_station_code = serializers.CharField(source='source_station.code', read_only=True)
    source_station_name = serializers.CharField(source='source_station.name', read_only=True)
    destination_station_code = serializers.CharField(source='destination_station.code', read_only=True)
    destination_station_name = serializers.CharField(source='destination_station.name', read_only=True)
    user_name = serializers.CharField(source='user.username', read_only=True)

    class Meta:
        model = Booking
        fields = ['id', 'user', 'user_name', 'train', 'train_number', 'train_name', 
                 'source_station', 'source_station_code', 'source_station_name',
                 'destination_station', 'destination_station_code', 'destination_station_name',
                 'travel_date', 'booking_status', 'quota', 'class_type', 'total_fare', 
                 'pnr_number', 'passengers', 'created_at', 'updated_at']
        read_only_fields = ['id', 'user', 'total_fare', 'pnr_number', 'booking_status', 'created_at', 'updated_at']

class PassengerCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Passenger
        fields = ['name', 'age', 'gender', 'berth_preference']

    def validate_age(self, value):
        if value < 1 or value > 120:
            raise serializers.ValidationError("Age must be between 1 and 120 years.")
        return value

class BookingCreateSerializer(serializers.ModelSerializer):
    passengers = PassengerCreateSerializer(many=True)
    train_id = serializers.IntegerField(write_only=True)
    source_station_code = serializers.CharField(write_only=True)
    destination_station_code = serializers.CharField(write_only=True)

    class Meta:
        model = Booking
        fields = ['train_id', 'source_station_code', 'destination_station_code', 
                 'travel_date', 'class_type', 'quota', 'passengers']

    def validate_train_id(self, value):
        if not Train.objects.filter(id=value).exists():
            raise serializers.ValidationError("Train does not exist.")
        return value

    def validate_source_station_code(self, value):
        if not Station.objects.filter(code=value).exists():
            raise serializers.ValidationError("Source station does not exist.")
        return value

    def validate_destination_station_code(self, value):
        if not Station.objects.filter(code=value).exists():
            raise serializers.ValidationError("Destination station does not exist.")
        return value

    def validate_travel_date(self, value):
        if value < timezone.now().date():
            raise serializers.ValidationError("Travel date cannot be in the past.")
        return value

    def validate_passengers(self, value):
        if not value:
            raise serializers.ValidationError("At least one passenger is required.")
        if len(value) > 6:
            raise serializers.ValidationError("Maximum 6 passengers allowed per booking.")
        return value

    def validate(self, data):
        train = Train.objects.get(id=data['train_id'])
        source_station = Station.objects.get(code=data['source_station_code'])
        destination_station = Station.objects.get(code=data['destination_station_code'])
        travel_date = data['travel_date']
        quota = data.get('quota', 'General')  # Default to General

        # Validate train runs on the specified date
        if not self._train_runs_on_date(train, travel_date):
            raise serializers.ValidationError("Train does not run on the specified date.")

        # Validate route exists and source comes before destination
        if not self._validate_route_order(train, source_station, destination_station):
            raise serializers.ValidationError("Invalid route: source station must come before destination station.")

        # Validate seat availability
        available_seats = self._get_available_seats(train, source_station, destination_station, 
                                                   travel_date, data['class_type'], quota)
        if available_seats < len(data['passengers']):
            raise serializers.ValidationError(f"Only {available_seats} seats available. Requested: {len(data['passengers'])}")

        return data

    def _train_runs_on_date(self, train, travel_date):
        """Check if train runs on the specified date"""
        # Get day of week (0=Monday, 6=Sunday)
        day_of_week = travel_date.weekday()
        day_codes = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
        day_code = day_codes[day_of_week]
        # day_names = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
        # day_name = day_names[day_of_week]
        
        return day_code in train.running_days

    def _validate_route_order(self, train, source_station, destination_station):
        """Validate that source station comes before destination in train route"""
        source_stop = TrainRouteStop.objects.filter(train=train, station=source_station).first()
        dest_stop = TrainRouteStop.objects.filter(train=train, station=destination_station).first()
        
        if not source_stop or not dest_stop:
            return False
        
        return source_stop.sequence < dest_stop.sequence

    def _get_available_seats(self, train, source_station, destination_station, travel_date, class_type, quota):
        """Calculate available seats for the route"""
        try:
            train_class = TrainClass.objects.get(train=train, class_type=class_type)
            total_seats = train_class.seat_capacity
            
            # Count booked seats for this route and date
            booked_seats = Booking.objects.filter(
                train=train,
                travel_date=travel_date,
                class_type=class_type,
                booking_status__in=['CONFIRMED', 'RAC']
            ).aggregate(total=Count('passengers'))['total'] or 0
            
            return max(0, total_seats - booked_seats)
        except TrainClass.DoesNotExist:
            return 0

class TrainSearchSerializer(serializers.Serializer):
    source_station = serializers.CharField()
    destination_station = serializers.CharField()
    travel_date = serializers.DateField()
    class_type = serializers.CharField(required=False, allow_blank=True)
    quota = serializers.CharField(required=False, allow_blank=True)

    def validate_source_station(self, value):
        if not Station.objects.filter(code=value).exists():
            raise serializers.ValidationError("Source station does not exist.")
        return value

    def validate_destination_station(self, value):
        if not Station.objects.filter(code=value).exists():
            raise serializers.ValidationError("Destination station does not exist.")
        return value

    def validate_travel_date(self, value):
        if value < timezone.now().date():
            raise serializers.ValidationError("Travel date cannot be in the past.")
        return value

class SeatAvailabilitySerializer(serializers.Serializer):
    train_id = serializers.IntegerField()
    source_station = serializers.CharField()
    destination_station = serializers.CharField()
    travel_date = serializers.DateField()
    class_type = serializers.CharField()
    quota = serializers.CharField()

    def validate_train_id(self, value):
        if not Train.objects.filter(id=value).exists():
            raise serializers.ValidationError("Train does not exist.")
        return value

    def validate_source_station(self, value):
        if not Station.objects.filter(code=value).exists():
            raise serializers.ValidationError("Source station does not exist.")
        return value

    def validate_destination_station(self, value):
        if not Station.objects.filter(code=value).exists():
            raise serializers.ValidationError("Destination station does not exist.")
        return value

    def validate_travel_date(self, value):
        if value < timezone.now().date():
            raise serializers.ValidationError("Travel date cannot be in the past.")
        return value 