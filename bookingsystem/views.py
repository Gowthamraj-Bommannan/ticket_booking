from django.shortcuts import render
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from django.db.models import Q, Count
from django.utils import timezone
from datetime import datetime, timedelta
from .models import Booking, Passenger
from .serializers import (
    BookingSerializer, BookingCreateSerializer, PassengerSerializer,
    TrainSearchSerializer, SeatAvailabilitySerializer
)
from trains.models import Train, TrainClass
from stations.models import Station
from routes.models import TrainRouteStop
import random, string
from bookingsystem.services import release_seats_and_promote
from decimal import Decimal

class BookingViewSet(viewsets.ModelViewSet):
    queryset = Booking.objects.all()
    serializer_class = BookingSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """Filter bookings for current user"""
        return Booking.objects.filter(user=self.request.user)

    def get_serializer_class(self):
        if self.action == 'create':
            return BookingCreateSerializer
        return BookingSerializer

    def perform_create(self, serializer):
        """Create booking with automatic seat allocation"""
        booking = serializer.save()
        self._allocate_seats(booking)
        return booking

    def _allocate_seats(self, booking):
        """Allocate seats to passengers based on availability"""
        passengers = booking.passengers.all()
        available_seats = self._get_available_seats_for_booking(booking)
        
        if available_seats >= len(passengers):
            # All passengers confirmed
            for i, passenger in enumerate(passengers):
                passenger.seat_number = f"{booking.class_type[0]}{i+1:03d}"
                passenger.booking_status = 'CONFIRMED'
                passenger.save()
            booking.booking_status = 'CONFIRMED'
        else:
            # Partial allocation - RAC/WL
            for i, passenger in enumerate(passengers):
                if i < available_seats:
                    passenger.seat_number = f"{booking.class_type}-{i+1:03d}"
                    passenger.booking_status = 'RAC'
                else:
                    passenger.booking_status = 'WL'
                passenger.save()
            booking.booking_status = 'RAC' if available_seats > 0 else 'WL'
        
        booking.save()

    def _get_available_seats_for_booking(self, booking):
        """Get available seats for specific booking"""
        try:
            train_class = TrainClass.objects.get(
                train=booking.train, 
                class_type=booking.class_type
            )
            total_seats = train_class.seat_capacity
            
            booked_seats = Booking.objects.filter(
                train=booking.train,
                travel_date=booking.travel_date,
                class_type=booking.class_type,
                booking_status__in=['CONFIRMED', 'RAC']
            ).exclude(id=booking.id).aggregate(
                total=Count('passengers')
            )['total'] or 0
            
            return max(0, total_seats - booked_seats)
        except TrainClass.DoesNotExist:
            return 0

    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        """Cancel a booking with refund calculation"""
        booking = self.get_object()
        
        if booking.booking_status == 'CANCELLED':
            return Response(
                {'detail': 'Booking is already cancelled.'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Calculate refund based on cancellation time
        refund_amount = self._calculate_refund(booking)
        
        # Update booking status
        booking.booking_status = 'CANCELLED'
        booking.save()
        
        # Release seats and auto-promote RAC/WL
        release_seats_and_promote(booking)
        
        return Response({
            'detail': 'Booking cancelled successfully.',
            'refund_amount': refund_amount,
            'pnr_number': booking.pnr_number
        })

    def _calculate_refund(self, booking):
        """Calculate refund amount based on cancellation time"""
        travel_date = booking.travel_date
        current_date = timezone.now().date()
        days_before = (travel_date - current_date).days
        
        if days_before >= 7:
            refund_percentage = 0.90  # 90% refund
        elif days_before >= 3:
            refund_percentage = 0.75  # 75% refund
        elif days_before >= 1:
            refund_percentage = 0.50  # 50% refund
        else:
            refund_percentage = 0.00  # No refund
        
        return booking.total_fare * refund_percentage

    @action(detail=False, methods=['get'])
    def history(self, request):
        """Get booking history for current user"""
        bookings = self.get_queryset().order_by('-created_at')
        serializer = self.get_serializer(bookings, many=True)
        return Response(serializer.data)
    
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        # Extract validated data
        validated_data = serializer.validated_data
        passengers_data = validated_data.pop('passengers')
        train = Train.objects.get(id=validated_data.pop('train_id'))
        source_station = Station.objects.get(code=validated_data.pop('source_station_code'))
        destination_station = Station.objects.get(code=validated_data.pop('destination_station_code'))
        
        # Calculate total fare
        total_fare = self._calculate_total_fare(
            train, source_station, destination_station,
            validated_data['class_type'], validated_data['quota'],
            len(passengers_data)
        )
        
        # Create booking with business logic moved from serializer
        booking = Booking.objects.create(
            user=request.user,
            train=train,
            source_station=source_station,
            destination_station=destination_station,
            total_fare=total_fare,
            booking_status='INITIATED',
            travel_date=validated_data['travel_date'],
            class_type=validated_data['class_type'],
            quota=validated_data['quota']
        )
        
        # Create passengers
        for passenger_data in passengers_data:
            Passenger.objects.create(booking=booking, **passenger_data)
        
        payment_session_id = ''.join(random.choices(string.ascii_uppercase + string.digits, k=12))
        return Response({
            "booking_id": booking.id,
            "payment_session_id": payment_session_id,
            "total_fare": float(total_fare)
        }, status=status.HTTP_201_CREATED)
    
    def _calculate_total_fare(self, train, source_station, destination_station, class_type, quota, passenger_count):
        """Calculate total fare for the booking"""
        # Get distance between stations
        source_stop = TrainRouteStop.objects.filter(train=train, station=source_station).order_by('sequence').first()
        dest_stop = TrainRouteStop.objects.filter(train=train, station=destination_station).order_by('sequence').first()
        distance = dest_stop.distance_from_source - source_stop.distance_from_source if source_stop and dest_stop else 0
        
        # Base fare rates per km (simplified)
        fare_rates = {
            'General': Decimal('1.50'),
            'Sleeper': Decimal('2.00'),
            'AC': Decimal('4.00'),
        }
        
        base_rate = fare_rates.get(class_type, Decimal('2.00'))
        base_fare = distance * base_rate
        
        # Add quota adjustments
        quota_multipliers = {
            'General': Decimal('1.00'),
            'Ladies': Decimal('0.75'),
            'Senior_Citizen': Decimal('0.50'),
            'Tatkal': Decimal('1.50'),
        }
        quota_multiplier = quota_multipliers.get(quota, Decimal('1.00'))
        
        total_fare = base_fare * quota_multiplier * passenger_count
        return total_fare

class TrainSearchViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]

    def list(self, request):
        """Search for trains between stations"""
        serializer = TrainSearchSerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        
        search_params = self._extract_search_params(serializer.validated_data)
        trains = self._find_running_trains(search_params['travel_date'])
        available_trains = self._filter_available_trains(trains, search_params)
        
        return Response(available_trains)
    
    def _extract_search_params(self, validated_data):
        """Extract search parameters from validated data"""
        return {
            'source_code': validated_data['source_station'],
            'dest_code': validated_data['destination_station'],
            'travel_date': validated_data['travel_date'],
            'class_type': validated_data.get('class_type', ''),
            'quota': validated_data.get('quota', '')
        }
    
    def _find_running_trains(self, travel_date):
        """Find trains running on the specified date"""
        day_of_week = travel_date.weekday()
        day_codes = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
        day_code = day_codes[day_of_week]
        
        return Train.objects.filter(running_days__contains=[day_code])
    
    def _filter_available_trains(self, trains, search_params):
        """Filter trains with available seats"""
        available_trains = []
        
        for train in trains:
            if self._has_valid_route(train, search_params['source_code'], search_params['dest_code']):
                availability = self._get_seat_availability(
                    train, search_params['source_code'], search_params['dest_code'], 
                    search_params['travel_date'], search_params['class_type'], search_params['quota']
                )
                if availability['available_seats'] > 0:
                    available_trains.append(self._format_train_info(train, search_params, availability))
        
        return available_trains
    
    def _format_train_info(self, train, search_params, availability):
        """Format train information for response"""
        return {
            'train_id': train.id,
            'train_number': train.train_number,
            'train_name': train.name,
            'train_type': train.train_type,
            'source_station': search_params['source_code'],
            'destination_station': search_params['dest_code'],
            'travel_date': search_params['travel_date'],
            'available_seats': availability['available_seats'],
            'class_types': availability['class_types']
        }

    def _has_valid_route(self, train, source_code, dest_code):
        """Check if train has valid route between stations"""
        source_stop = TrainRouteStop.objects.filter(
            train=train, 
            station__code=source_code
        ).first()
        dest_stop = TrainRouteStop.objects.filter(
            train=train, 
            station__code=dest_code
        ).first()
        
        return source_stop and dest_stop and source_stop.sequence < dest_stop.sequence

    def _get_seat_availability(self, train, source_code, dest_code, travel_date, class_type, quota):
        """Get seat availability for train"""
        try:
            if class_type:
                train_classes = TrainClass.objects.filter(train=train, class_type=class_type)
            else:
                train_classes = TrainClass.objects.filter(train=train)
            
            availability = {
                'available_seats': 0,
                'class_types': {}
            }
            
            for tc in train_classes:
                total_seats = tc.seat_capacity
                booked_seats = Booking.objects.filter(
                    train=train,
                    travel_date=travel_date,
                    class_type=tc.class_type,
                    booking_status__in=['CONFIRMED', 'RAC']
                ).aggregate(total=Count('passengers'))['total'] or 0
                
                available = max(0, total_seats - booked_seats)
                availability['class_types'][tc.class_type] = available
                availability['available_seats'] += available
            
            return availability
        except Exception:
            return {'available_seats': 0, 'class_types': {}}

class SeatAvailabilityViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]

    def list(self, request):
        """Get detailed seat availability for a specific train"""
        serializer = SeatAvailabilitySerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        
        train_id = serializer.validated_data['train_id']
        source_code = serializer.validated_data['source_station']
        dest_code = serializer.validated_data['destination_station']
        travel_date = serializer.validated_data['travel_date']
        class_type = serializer.validated_data['class_type']
        quota = serializer.validated_data['quota']
        
        train = get_object_or_404(Train, id=train_id)
        
        # Get detailed availability
        availability = self._get_detailed_availability(
            train, source_code, dest_code, travel_date, class_type, quota
        )
        
        return Response(availability)

    def _get_detailed_availability(self, train, source_code, dest_code, travel_date, class_type, quota):
        """Get detailed seat availability breakdown"""
        try:
            train_class = TrainClass.objects.get(train=train, class_type=class_type)
            total_seats = train_class.seat_capacity
            
            # Get booked seats
            booked_seats = Booking.objects.filter(
                train=train,
                travel_date=travel_date,
                class_type=class_type,
                booking_status__in=['CONFIRMED', 'RAC']
            ).aggregate(total=Count('passengers'))['total'] or 0
            
            available_seats = max(0, total_seats - booked_seats)
            
            # Get waitlist count
            waitlist_count = Booking.objects.filter(
                train=train,
                travel_date=travel_date,
                class_type=class_type,
                booking_status='WL'
            ).aggregate(total=Count('passengers'))['total'] or 0
            
            return {
                'train_id': train.id,
                'train_number': train.train_number,
                'train_name': train.name,
                'source_station': source_code,
                'destination_station': dest_code,
                'travel_date': travel_date,
                'class_type': class_type,
                'quota': quota,
                'total_seats': total_seats,
                'booked_seats': booked_seats,
                'available_seats': available_seats,
                'waitlist_count': waitlist_count,
                'status': 'Available' if available_seats > 0 else 'Waitlist'
            }
        except TrainClass.DoesNotExist:
            return {
                'error': 'Train class not found',
                'status': 'Not Available'
            }
