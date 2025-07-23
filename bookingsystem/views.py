import logging
from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import action
from django.shortcuts import get_object_or_404
from django.utils import timezone
from .models import Booking
from .serializers import BookingSerializer
from stations.models import Station
from exceptions.handlers import (
    StationNotFoundException,
    FromAndToMustBeDifferent,
    NewToStationRequired,
    OnlyBookedTicketsExchanged,
    FromAndToStationsRequired,
    BookingUnauthorizedException,
)
from .services import (
    generate_unique_ticket_number,
    calculate_fare,
    get_next_available_trains,
)
from datetime import timedelta

logger = logging.getLogger("bookingsystem")


class IsRegularUser(IsAuthenticated):
    def has_permission(self, request, view):
        is_authenticated = super().has_permission(request, view)
        if view.action == "create":
            return is_authenticated and not (
                request.user.is_staff or request.user.is_superuser
            )
        return is_authenticated


class BookingViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing bookings.
    Supports CRUD operations and custom actions.
    """

    queryset = Booking.objects.all()
    serializer_class = BookingSerializer
    permission_classes = [IsRegularUser]

    def get_queryset(self):
        """Return only the user's bookings, sorted by newest first"""
        if self.request.user.is_staff or self.request.user.is_superuser:
            return Booking.objects.all().order_by("-created_at")
        return Booking.objects.filter(user=self.request.user).order_by("-created_at")

    def create(self, request, *args, **kwargs):
        """
        Handles booking creation requests.
        Validates and creates a new booking.
        """
        if request.user.is_staff or request.user.is_superuser:
            logger.warning(
                f"Admin/staff user {request.user} attempted to create a booking."
            )
            return Response(
                {"detail": "Admins and staff cannot create bookings."},
                status=status.HTTP_403_FORBIDDEN,
            )
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        validated_data = serializer.validated_data

        from_code = validated_data["from_station_code"].strip().upper()
        to_code = validated_data["to_station_code"].strip().upper()
        from_station = Station.objects.get(code__iexact=from_code)
        to_station = Station.objects.get(code__iexact=to_code)

        # Calculate total fare
        total_fare = calculate_fare(
            validated_data["class_type"], validated_data["num_of_passenegers"]
        )
        ticket_number = generate_unique_ticket_number()

        booking_time = timezone.now()
        expiry_time = booking_time + timedelta(hours=1)
        booking = Booking.objects.create(
            user=request.user,
            from_station=from_station,
            to_station=to_station,
            class_type=validated_data["class_type"],
            num_of_passenegers=validated_data["num_of_passenegers"],
            total_fare=total_fare,
            travel_date=timezone.now().date(),
            ticket_number=ticket_number,
            booking_status="PENDING",
            booking_time=booking_time,
            expiry_time=expiry_time,
        )

        logger.info(
            f"Booking created: user={request.user}, from={from_code}, to={to_code}, class={validated_data['class_type']}, num={validated_data['num_of_passenegers']}, ticket={ticket_number}"
        )

        response_serializer = self.get_serializer(booking)
        return Response(
            {
                "message": "Booking initiated successfully! Please complete the payment.",
                "booking_id": booking.id,
                "ticket_number": ticket_number,
                "total_fare": float(total_fare),
                "booking_details": response_serializer.data,
            },
            status=status.HTTP_201_CREATED,
        )

    @action(detail=False, methods=["get"], url_path="check-availability")
    def check_availability(self, request):
        """Check available trains for a route"""
        from_station_code = request.query_params.get("from_station")
        to_station_code = request.query_params.get("to_station")
        class_type = request.query_params.get("class_type", "GENERAL")

        if not from_station_code or not to_station_code:
            raise FromAndToStationsRequired()

        try:
            from_station = Station.objects.get(code__iexact=from_station_code)
            to_station = Station.objects.get(code__iexact=to_station_code)
        except Station.DoesNotExist:
            raise StationNotFoundException()

        # Get available trains
        available_trains = get_next_available_trains(
            from_station, to_station, class_type
        )

        return Response(
            {
                "from_station": from_station.name,
                "to_station": to_station.name,
                "class_type": class_type,
                "available_trains": available_trains,
                "total_available": len(available_trains),
            }
        )

    def list(self, request, *args, **kwargs):
        """
        Lists all bookings.
        Supports filtering and pagination.
        """
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)

        # Add summary information
        total_bookings = queryset.count()
        pending_bookings = queryset.filter(booking_status="PENDING").count()
        booked_tickets = queryset.filter(booking_status="BOOKED").count()
        failed_bookings = queryset.filter(booking_status="FAILED").count()

        return Response(
            {
                "total_bookings": total_bookings,
                "pending_bookings": pending_bookings,
                "booked_tickets": booked_tickets,
                "failed_bookings": failed_bookings,
                "bookings": serializer.data,
            }
        )

    def retrieve(self, request, *args, **kwargs):
        """
        Retrieves a booking by ID.
        Returns booking details.
        """
        booking = self.get_object()
        if booking.user != request.user and not (
            request.user.is_staff or request.user.is_superuser
        ):
            logger.warning(
                f"User {request.user} attempted to access booking {booking.id} belonging to {booking.user}"
            )
            raise BookingUnauthorizedException()
        serializer = self.get_serializer(booking)
        return Response(serializer.data)

    def update(self, request, *args, **kwargs):
        """
        Handles booking update requests.
        Updates booking details or status.
        """
        return Response(
            {"detail": "Ticket update is not allowed."},
            status=status.HTTP_405_METHOD_NOT_ALLOWED,
        )

    @action(detail=True, methods=["post"], url_path="exchange")
    def exchange_ticket(self, request, pk=None):
        """Exchange ticket - change destination station only"""
        booking = self.get_object()

        # Only allow exchange for BOOKED tickets
        if booking.booking_status != "BOOKED":
            raise OnlyBookedTicketsExchanged()

        # Get new destination station
        new_to_station_code = request.data.get("to_station_code")
        if not new_to_station_code:
            raise NewToStationRequired()

        try:
            new_to_station = Station.objects.get(
                code__iexact=new_to_station_code.strip()
            )
        except Station.DoesNotExist:
            raise StationNotFoundException()

        # Validate that new destination is different from current
        if booking.to_station == new_to_station:
            raise FromAndToMustBeDifferent()

        # Validate that new destination is different from source
        if booking.from_station == new_to_station:
            raise FromAndToMustBeDifferent()

        # Update the destination station
        old_destination = booking.to_station.name
        booking.to_station = new_to_station
        booking.save()

        logger.info(
            f"Ticket exchange: user={request.user}, booking_id={booking.id}, old_to={old_destination}, new_to={new_to_station.name}"
        )

        return Response(
            {
                "message": f"Ticket exchanged successfully! Destination changed from {old_destination} to {new_to_station.name}",
                "ticket_number": booking.ticket_number,
                "old_destination": old_destination,
                "new_destination": new_to_station.name,
                "booking_details": self.get_serializer(booking).data,
            },
            status=status.HTTP_200_OK,
        )

    def destroy(self, request, *args, **kwargs):
        """
        Deletes a booking.
        Removes booking record from database.
        """
        return Response(
            {
                "error": "Cancellation is not allowed for local train tickets. Use ticket exchange if needed."
            },
            status=status.HTTP_405_METHOD_NOT_ALLOWED,
        )

    def get_object(self):
        """Get booking object with user-specific access"""
        queryset = self.get_queryset()
        lookup_url_kwarg = self.lookup_url_kwarg or self.lookup_field
        filter_kwargs = {self.lookup_field: self.kwargs[lookup_url_kwarg]}
        obj = get_object_or_404(queryset, **filter_kwargs)
        self.check_object_permissions(self.request, obj)
        return obj
