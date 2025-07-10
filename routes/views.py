from django.shortcuts import render
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import BasePermission, IsAuthenticated
from django.db import transaction
from rest_framework import serializers
from datetime import datetime, timedelta
from .models import TrainRouteStop, RouteTemplate, RouteTemplateStop
from .serializers import (
    TrainRouteStopSerializer, TrainRouteStopCreateSerializer, 
    TrainRouteStopUpdateSerializer, TrainRouteSerializer,
    RouteTemplateSerializer, RouteTemplateStopSerializer,
    CreateTrainFromTemplateSerializer,
    TrainRouteStopArrivalUpdateSerializer
)
from trains.models import Train
from stations.models import Station
from exceptions.handlers import (
    RouteNotFoundException, RouteAlreadyDefinedException,
    RouteStopNotFoundException, RouteStopStationInactiveException,
    RouteStopTrainInactiveException, RouteStopInvalidInputException
)
import logging
logger = logging.getLogger("routes")

class IsAdminUser(BasePermission):
    """
    Allows access only to admin users.
    """
    def has_permission(self, request, view):
        logger.info(f"Checking admin permission for user: {request.user.id if request.user else 'Anonymous'}")
        permission_granted = bool(
            request.user and 
            request.user.is_authenticated and
            request.user.role == 'admin'
        )
        logger.info(f"Admin permission granted: {permission_granted}")
        return permission_granted

class IsStationMaster(BasePermission):
    """
    Allows access only to station master users.
    """
    def has_permission(self, request, view):
        logger.info(f"Checking station master permission for user: {request.user.id if request.user else 'Anonymous'}")
        permission_granted = bool(
            request.user and 
            request.user.is_authenticated and
            request.user.role == 'station_master'
        )
        logger.info(f"Station master permission granted: {permission_granted}")
        return permission_granted

class TrainRouteViewSet(viewsets.ModelViewSet):
    """
    Provides endpoints for managing train route stops.
    """
    queryset = TrainRouteStop.objects.all()
    serializer_class = TrainRouteStopSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = 'id'

    def get_queryset(self):
        """
        Returns the queryset of route stops, filtered by train if provided.
        """
        qs = super().get_queryset()
        train_number = self.kwargs.get('train_number')
        if train_number:
            qs = qs.filter(train__train_number=train_number)
        return qs.order_by('train', 'sequence')

    def get_permissions(self):
        """
        Returns the appropriate permissions based on the action.
        """
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            if self.action == 'partial_update' and self.request.user.role == 'station_master':
                permission_classes = [IsStationMaster]
            else:
                permission_classes = [IsAdminUser]
        else:
            permission_classes = [IsAuthenticated]
        return [permission() for permission in permission_classes]

    @action(detail=False, methods=['post'], url_path='train/(?P<train_number>[^/.]+)/add-stop')
    def add_stop(self, request, train_number=None):
        """
        Adds a new stop to a train route.
        """
        logger.info(f"Attempting to add stop for train {train_number} by user {request.user.id if request.user else 'Anonymous'}")
        train = Train.objects.filter(train_number=train_number).first()
        if not train:
            raise RouteStopTrainInactiveException()
        if not train.is_active:
            raise RouteStopTrainInactiveException()
        serializer = TrainRouteStopCreateSerializer(
            data=request.data, 
            context={'train': train}
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        logger.info(f"Stop added successfully for train {train_number} by user {request.user.id if request.user else 'Anonymous'}")
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=['patch'], url_path='train/(?P<train_number>[^/.]+)/stations/(?P<station_code>[^/.]+)')
    def update_stop(self, request, train_number=None, station_code=None):
        """
        Updates a specific stop in a train route.
        """
        logger.info(f"Attempting to update stop for train {train_number} and station {station_code} by user {request.user.id if request.user else 'Anonymous'}")
        train = Train.objects.filter(train_number=train_number).first()
        if not train:
            raise RouteStopTrainInactiveException()
        if not train.is_active:
            raise RouteStopTrainInactiveException()
        station = Station.objects.filter(code=station_code).first()
        if not station:
            raise RouteStopNotFoundException()
        if not station.is_active:
            raise RouteStopStationInactiveException()
        route_stop = TrainRouteStop.objects.filter(train=train, station=station).first()
        if not route_stop:
            raise RouteStopNotFoundException()
        # Check if user is station master and can only update their station
        if request.user.role == 'station_master':
            if not hasattr(request.user, 'station') or request.user.station != station:
                raise RouteStopInvalidInputException()
            allowed_fields = ['scheduled_arrival_time', 'scheduled_departure_time']
            data = {k: v for k, v in request.data.items() if k in allowed_fields}
        else:
            data = request.data
        serializer = TrainRouteStopUpdateSerializer(route_stop, data=data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        logger.info(f"Stop updated successfully for train {train_number} and station {station_code} by user {request.user.id if request.user else 'Anonymous'}")
        return Response(serializer.data)

    @action(detail=False, methods=['delete'], url_path='train/(?P<train_number>[^/.]+)/stations/(?P<station_code>[^/.]+)')
    def delete_stop(self, request, train_number=None, station_code=None):
        """
        Deletes a stop and re-adjusts sequences in a train route.
        """
        logger.info(f"Attempting to delete stop for train {train_number} and station {station_code} by user {request.user.id if request.user else 'Anonymous'}")
        train = Train.objects.filter(train_number=train_number).first()
        if not train:
            raise RouteStopTrainInactiveException()
        if not train.is_active:
            raise RouteStopTrainInactiveException()
        station = Station.objects.filter(code=station_code).first()
        if not station:
            raise RouteStopNotFoundException()
        if not station.is_active:
            raise RouteStopStationInactiveException()
        route_stop = TrainRouteStop.objects.filter(train=train, station=station).first()
        if not route_stop:
            raise RouteStopNotFoundException()
        with transaction.atomic():
            remaining_stops = TrainRouteStop.objects.filter(
                train=train, 
                sequence__gt=route_stop.sequence
            ).order_by('sequence')
            for stop in remaining_stops:
                stop.sequence -= 1
                stop.save()
            route_stop.delete()
        logger.info(f"Stop deleted successfully for train {train_number} and station {station_code} by user {request.user.id if request.user else 'Anonymous'}")
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=False, methods=['get'], url_path='train/(?P<train_number>[^/.]+)')
    def get_route(self, request, train_number=None):
        """
        Retrieves the full route for a train.
        """
        logger.info(f"Attempting to get route for train {train_number} by user {request.user.id if request.user else 'Anonymous'}")
        train = Train.objects.filter(train_number=train_number).first()
        if not train:
            raise RouteStopTrainInactiveException()
        if not train.is_active:
            raise RouteStopTrainInactiveException()
        serializer = TrainRouteSerializer(train)
        logger.info(f"Route retrieved successfully for train {train_number} by user {request.user.id if request.user else 'Anonymous'}")
        return Response(serializer.data)

    @action(detail=False, methods=['patch'], url_path='train/(?P<train_number>[^/.]+)/stations/(?P<station_code>[^/.]+)/update-arrival')
    def update_actual_arrival(self, request, train_number=None, station_code=None):
        """
        Allows station master to update actual arrival time and auto-update actual departure time. Propagates delay to subsequent stops.
        """
        logger.info(f"Updating actual arrival for train {train_number} at station {station_code} by user {request.user.username}")
        
        try:
            # Validate and get required objects
            train, station, route_stop = self._validate_arrival_update_request(train_number, station_code)
            
            # Check permissions
            self._check_station_master_permission(request.user, station, station_code)
            
            # Update arrival time
            serializer = self._update_arrival_time(route_stop, request.data)
            
            # Propagate delay if needed
            self._propagate_delay_if_needed(train, route_stop, serializer)
            
            logger.info(f"Arrival update complete for train {train_number} at station {station_code}")
            return Response(serializer.data)
            
        except Exception as e:
            logger.error(f"Error updating arrival for train {train_number} at station {station_code}: {str(e)}", exc_info=True)
            raise RouteStopInvalidInputException(f"Failed to update arrival time: {str(e)}")

    def _validate_arrival_update_request(self, train_number, station_code):
        """
        Validates the request and returns train, station, and route_stop objects.
        """
        train = Train.objects.filter(train_number=train_number).first()
        if not train or not train.is_active:
            logger.warning(f"Train not found or inactive: {train_number}")
            raise RouteStopTrainInactiveException()
            
        station = Station.objects.filter(code=station_code).first()
        if not station or not station.is_active:
            logger.warning(f"Station not found or inactive: {station_code}")
            raise RouteStopStationInactiveException()
            
        route_stop = TrainRouteStop.objects.filter(train=train, station=station).first()
        if not route_stop:
            logger.warning(f"Route stop not found for train {train_number} at station {station_code}")
            raise RouteStopNotFoundException()
            
        return train, station, route_stop

    def _check_station_master_permission(self, user, station, station_code):
        """
        Checks if user has station master permission for the given station.
        """
        if user.role != 'station_master' or not hasattr(user, 'station') or user.station != station:
            logger.warning(f"Unauthorized access: user {user.username} is not station master for station {station_code}")
            from exceptions.handlers import UnauthorizedAccessException
            raise UnauthorizedAccessException()

    def _update_arrival_time(self, route_stop, data):
        """
        Updates the actual arrival time and calculates departure time.
        """
        serializer = TrainRouteStopArrivalUpdateSerializer(
            route_stop, 
            data=data, 
            context={'request': None}, 
            partial=True
        )
        
        try:
            serializer.is_valid(raise_exception=True)
        except serializers.ValidationError as e:
            logger.error(f"Serializer validation failed: {e.detail}")
            raise RouteStopInvalidInputException(f"Validation error: {e.detail}")
        except Exception as e:
            logger.error(f"Unexpected error during serializer validation: {str(e)}", exc_info=True)
            raise RouteStopInvalidInputException(f"Serializer error: {str(e)}")
        
        with transaction.atomic():
            instance = serializer.save()
            logger.info(f"Updated arrival time: {instance.actual_arrival_time}, departure time: {instance.actual_departure_time}")
            return serializer

    def _propagate_delay_if_needed(self, train, route_stop, serializer):
        """
        Propagates delay to subsequent stops if there's a delay.
        """
        from datetime import datetime, timedelta
        
        scheduled = route_stop.scheduled_departure_time
        actual = serializer.instance.actual_departure_time
        
        if scheduled and actual and actual > scheduled:
            delay = (datetime.combine(datetime.today(), actual) - 
                    datetime.combine(datetime.today(), scheduled)).total_seconds() / 60
            logger.info(f"Delay detected: {delay} minutes, propagating to subsequent stops")
            
            if delay > 0:
                self._update_subsequent_stops(train, route_stop, delay)
        else:
            logger.info("No delay detected")

    def _update_subsequent_stops(self, train, route_stop, delay):
        """
        Updates all subsequent stops with the calculated delay.
        """
        from datetime import datetime, timedelta
        
        subsequent_stops = TrainRouteStop.objects.filter(
            train=train, 
            sequence__gt=route_stop.sequence
        ).order_by('sequence')
        
        logger.info(f"Updating {subsequent_stops.count()} subsequent stops")
        
        for stop in subsequent_stops:
            self._update_single_stop(stop, delay, train)

    def _update_single_stop(self, stop, delay, train):
        """
        Updates a single stop with the delay and calculates actual times if needed.
        """
        from datetime import datetime, timedelta
        
        # Store old values for logging
        old_sched_arr = stop.scheduled_arrival_time
        old_sched_dep = stop.scheduled_departure_time
        
        # Update scheduled times
        if stop.scheduled_arrival_time:
            arr_dt = datetime.combine(datetime.today(), stop.scheduled_arrival_time) + timedelta(minutes=delay)
            stop.scheduled_arrival_time = arr_dt.time()
        
        if stop.scheduled_departure_time:
            dep_dt = datetime.combine(datetime.today(), stop.scheduled_departure_time) + timedelta(minutes=delay)
            stop.scheduled_departure_time = dep_dt.time()
        
        # Update actual times if they exist
        self._update_actual_times_if_exist(stop, delay)
        
        # Calculate actual times if train has departed from previous station
        self._calculate_actual_times_if_needed(stop, train)
        
        stop.save()
        logger.info(f"Updated {stop.station.code}: sched_arr={old_sched_arr}->{stop.scheduled_arrival_time}, "
                  f"sched_dep={old_sched_dep}->{stop.scheduled_departure_time}")

    def _update_actual_times_if_exist(self, stop, delay):
        """
        Updates actual times if they already exist.
        """
        from datetime import datetime, timedelta
        
        if stop.actual_arrival_time:
            arr_dt = datetime.combine(datetime.today(), stop.actual_arrival_time) + timedelta(minutes=delay)
            stop.actual_arrival_time = arr_dt.time()
        
        if stop.actual_departure_time:
            dep_dt = datetime.combine(datetime.today(), stop.actual_departure_time) + timedelta(minutes=delay)
            stop.actual_departure_time = dep_dt.time()

    def _calculate_actual_times_if_needed(self, stop, train):
        """
        Calculates actual times if they don't exist but train has departed from previous station.
        """
        from datetime import datetime, timedelta
        
        if not stop.actual_arrival_time and not stop.actual_departure_time:
            prev_stop = TrainRouteStop.objects.filter(
                train=train, 
                sequence=stop.sequence - 1
            ).first()
            
            if prev_stop and prev_stop.actual_departure_time:
                self._set_actual_times_from_previous_stop(stop, prev_stop)

    def _set_actual_times_from_previous_stop(self, stop, prev_stop):
        """
        Sets actual times based on previous stop's actual departure time.
        """
        from datetime import datetime, timedelta
        
        if prev_stop.scheduled_departure_time and stop.scheduled_arrival_time:
            travel_time = (datetime.combine(datetime.today(), stop.scheduled_arrival_time) - 
                         datetime.combine(datetime.today(), prev_stop.scheduled_departure_time)).total_seconds() / 60
            
            # Set actual arrival time
            actual_arr_dt = datetime.combine(datetime.today(), prev_stop.actual_departure_time) + timedelta(minutes=travel_time)
            stop.actual_arrival_time = actual_arr_dt.time()
            
            # Set actual departure time
            if stop.halt_minutes:
                actual_dep_dt = actual_arr_dt + timedelta(minutes=stop.halt_minutes)
                stop.actual_departure_time = actual_dep_dt.time()

class RouteTemplateViewSet(viewsets.ModelViewSet):
    """
    Provides endpoints for managing route templates.
    """
    queryset = RouteTemplate.objects.all()
    serializer_class = RouteTemplateSerializer
    permission_classes = [IsAdminUser]
    lookup_field = 'id'

    def get_permissions(self):
        """
        Returns the appropriate permissions based on the action.
        """
        if self.action in ['list', 'retrieve']:
            permission_classes = [IsAuthenticated]
        else:
            permission_classes = [IsAdminUser]
        return [permission() for permission in permission_classes]

    @action(detail=True, methods=['post'], url_path='create-train-route')
    def create_train_route(self, request, pk=None, id=None):
        """
        Creates a train route from a route template.
        """
        logger.info(f"Attempting to create train route from template {pk} by user {request.user.id if request.user else 'Anonymous'}")
        route_template = self.get_object()
        serializer = CreateTrainFromTemplateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        train_number = serializer.validated_data['train_number']
        start_time = serializer.validated_data['start_time']
        train = Train.objects.filter(train_number=train_number).first()
        if not train:
            raise RouteStopTrainInactiveException()
        if not train.is_active:
            raise RouteStopTrainInactiveException()
        if TrainRouteStop.objects.filter(train=train).exists():
            raise RouteAlreadyDefinedException()
        try:
            with transaction.atomic():
                self._create_train_route_from_template(route_template, train, start_time)
            logger.info(f"Train route created successfully for train {train_number} from template {pk} by user {request.user.id if request.user else 'Anonymous'}")
            return Response({
                'detail': f'Route created successfully for train {train_number} from template "{route_template.name}"',
                'train_number': train_number,
                'template_name': route_template.name
            }, status=status.HTTP_201_CREATED)
        except Exception as e:
            logger.error(f"Error creating train route from template {pk}: {e}", exc_info=True)
            raise RouteStopInvalidInputException(str(e))

    def _create_train_route_from_template(self, route_template, train, start_time):
        """
        Internal: Creates all stops for a train from a template.
        """
        logger.info(f"Attempting to create train route stops from template {route_template.id} for train {train.train_number}")
        # Parse start time
        if isinstance(start_time, str):
            start_time = datetime.strptime(start_time, "%H:%M:%S").time()
        
        # Get template stops ordered by sequence
        template_stops = route_template.template_stops.all().order_by('sequence')
        
        if not template_stops.exists():
            raise RouteNotFoundException()
        
        # Create source station stop
        self._create_source_stop(train, route_template, start_time)
        
        # Create intermediate stops
        current_time, current_day = self._create_intermediate_stops(train, template_stops, start_time)
        
        # Create destination station stop
        self._create_destination_stop(train, route_template, template_stops, current_time, current_day)
    
    def _create_source_stop(self, train, route_template, start_time):
        """
        Internal: Creates the source station stop for a train route.
        """
        logger.info(f"Creating source stop for train {train.train_number} from template {route_template.id}")
        source_stop = TrainRouteStop(
            train=train,
            station=route_template.source_station,
            sequence=1,
            scheduled_arrival_time=None,
            scheduled_departure_time=start_time,
            actual_arrival_time=None,
            actual_departure_time=None,
            halt_minutes=0,
            distance_from_source=0.0,
            day_count=1
        )
        source_stop.save()
        logger.info(f"Source stop created for train {train.train_number} from template {route_template.id}")
    
    def _create_intermediate_stops(self, train, template_stops, start_time):
        """
        Internal: Creates all intermediate stops for a train route.
        """
        logger.info(f"Attempting to create intermediate stops for train {train.train_number} from template {template_stops.first().route_template.id}")
        current_time = start_time
        current_day = 1
        prev_distance = 0.0
        
        for template_stop in template_stops:
            current_time, current_day = self._create_single_intermediate_stop(
                train, template_stop, current_time, current_day, prev_distance
            )
            prev_distance = template_stop.distance_from_source
        
        logger.info(f"Intermediate stops created for train {train.train_number} from template {template_stops.first().route_template.id}")
        return current_time, current_day
    
    def _create_single_intermediate_stop(self, train, template_stop, current_time, current_day, prev_distance):
        """
        Internal: Creates a single intermediate stop for a train route.
        """
        logger.info(f"Attempting to create single intermediate stop for train {train.train_number} from template {template_stop.route_template.id}")
        # Calculate arrival time based on distance and average speed
        distance_diff = template_stop.distance_from_source - prev_distance
        travel_minutes = int((distance_diff / 60) * 60)  # Assume 60 km/h
        
        # Calculate arrival time
        arrival_dt = datetime.combine(datetime.today(), current_time) + timedelta(minutes=travel_minutes)
        
        # Check if day changes
        if arrival_dt.date() > datetime.today().date():
            current_day += 1
            arrival_dt = arrival_dt.replace(hour=arrival_dt.hour, minute=arrival_dt.minute, second=arrival_dt.second)
        
        arrival_time = arrival_dt.time()
        
        halt_minutes = max(1, template_stop.estimated_halt_minutes)
        departure_dt = arrival_dt + timedelta(minutes=halt_minutes)
        departure_time = departure_dt.time()
        
        route_stop = TrainRouteStop(
            train=train,
            station=template_stop.station,
            sequence=template_stop.sequence + 1,
            scheduled_arrival_time=arrival_time,
            scheduled_departure_time=departure_time,
            actual_arrival_time=None,
            actual_departure_time=None,
            halt_minutes=halt_minutes,
            distance_from_source=template_stop.distance_from_source,
            day_count=current_day
        )
        route_stop.save()
        logger.info(f"Single intermediate stop created for train {train.train_number} from template {template_stop.route_template.id}")
        return departure_time, current_day
    
    def _create_destination_stop(self, train, route_template, template_stops, current_time, current_day):
        """
        Internal: Creates the destination station stop for a train route.
        """
        logger.info(f"Attempting to create destination stop for train {train.train_number} from template {route_template.id}")
        last_template_stop = template_stops.last()
        if not last_template_stop:
            return
        
        # Calculate arrival time to destination
        distance_diff = route_template.total_distance - last_template_stop.distance_from_source
        travel_minutes = int((distance_diff / 60) * 60)
        
        arrival_dt = datetime.combine(datetime.today(), current_time) + timedelta(minutes=travel_minutes)
        
        # Check if day changes
        if arrival_dt.date() > datetime.today().date():
            current_day += 1
        
        arrival_time = arrival_dt.time()
        
        dest_stop = TrainRouteStop(
            train=train,
            station=route_template.destination_station,
            sequence=last_template_stop.sequence + 2,
            scheduled_arrival_time=arrival_time,
            scheduled_departure_time=None,
            actual_arrival_time=None,
            actual_departure_time=None,
            halt_minutes=0,
            distance_from_source=route_template.total_distance,
            day_count=current_day
        )
        dest_stop.save()
        logger.info(f"Destination stop created for train {train.train_number} from template {route_template.id}")

class RouteTemplateStopViewSet(viewsets.ModelViewSet):
    """
    Provides endpoints for managing route template stops.
    """
    queryset = RouteTemplateStop.objects.all()
    serializer_class = RouteTemplateStopSerializer
    permission_classes = [IsAdminUser]
    lookup_field = 'id'

    def get_permissions(self):
        """
        Returns the appropriate permissions based on the action.
        """
        if self.action in ['list', 'retrieve']:
            permission_classes = [IsAuthenticated]
        else:
            permission_classes = [IsAdminUser]
        return [permission() for permission in permission_classes]

__all__ = ['TrainRouteViewSet', 'RouteTemplateViewSet', 'RouteTemplateStopViewSet', 'IsAdminUser', 'IsStationMaster']
