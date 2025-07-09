from django.shortcuts import render
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import BasePermission, IsAuthenticated
from django.db import transaction
from datetime import datetime, timedelta
from .models import TrainRouteStop, RouteTemplate, RouteTemplateStop
from .serializers import (
    TrainRouteStopSerializer, TrainRouteStopCreateSerializer, 
    TrainRouteStopUpdateSerializer, TrainRouteSerializer,
    RouteTemplateSerializer, RouteTemplateStopSerializer,
    CreateTrainFromTemplateSerializer
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
            allowed_fields = ['arrival_time', 'departure_time']
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
            arrival_time=None,
            departure_time=start_time,
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
        
        # Calculate departure time
        halt_minutes = max(1, template_stop.estimated_halt_minutes)
        departure_dt = arrival_dt + timedelta(minutes=halt_minutes)
        departure_time = departure_dt.time()
        
        # Create train route stop
        route_stop = TrainRouteStop(
            train=train,
            station=template_stop.station,
            sequence=template_stop.sequence + 1,
            arrival_time=arrival_time,
            departure_time=departure_time,
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
            arrival_time=arrival_time,
            departure_time=None,
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

# Expose ViewSets for router registration
__all__ = ['TrainRouteViewSet', 'RouteTemplateViewSet', 'RouteTemplateStopViewSet', 'IsAdminUser', 'IsStationMaster']
