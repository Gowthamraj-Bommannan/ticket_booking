from django.shortcuts import render
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import BasePermission, IsAuthenticated
from django.shortcuts import get_object_or_404
from django.http import Http404
from .models import Station
from accounts.models import User
from .serializers import StationSerializer, AssignStationMasterSerializer
from exceptions.handlers import (
    StationNotFoundException, StationAlreadyExistsException,
    UnauthorizedAccessException, NotFound, StationMasterExistsException
)
from utils.constants import UserMessage
import logging

logger = logging.getLogger("stations")

# Expose StationViewSet for router registration
__all__ = ['StationViewSet', 'IsAdminUser', 'IsAdminOrStationMaster']

class IsAdminUser(BasePermission):
    """
    Allows access only to admin users.
    """
    def has_permission(self, request, view):
        logger.info(f"Checking IsAdminUser permission for user: {request.user.id}")
        is_allowed = bool(request.user and request.user.is_authenticated and request.user.role == 'admin')
        logger.info(f"IsAdminUser permission check result: {is_allowed}")
        return is_allowed

class IsAdminOrStationMaster(BasePermission):
    """
    Allows access to admin users or station masters.
    """
    def has_permission(self, request, view):
        logger.info(f"Checking IsAdminOrStationMaster permission for user: {request.user.id}")
        is_allowed = bool(
            request.user and 
            request.user.is_authenticated and
            request.user.role in ['admin', 'station_master']
        )
        logger.info(f"IsAdminOrStationMaster permission check result: {is_allowed}")
        return is_allowed

class StationViewSet(viewsets.ModelViewSet):
    """
    Provides CRUD and soft delete endpoints for stations.
    """
    queryset = Station.objects.all()
    serializer_class = StationSerializer
    lookup_field = 'code'

    def get_permissions(self):
        """
        Returns the appropriate permissions based on the action.
        """
        logger.info(f"Getting permissions for action: {self.action}")
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            permission_classes = [IsAdminUser]
        elif self.action in ['deactivate', 'activate']:
            permission_classes = [IsAdminOrStationMaster]
        else:
            permission_classes = [IsAuthenticated]
        logger.info(f"Permission classes for action {self.action}: {[p.__name__ for p in permission_classes]}")
        return [permission() for permission in permission_classes]

    def get_queryset(self):
        """
        Returns the queryset of stations, filtered by city/state if provided.
        """
        logger.info("Getting queryset for StationViewSet")
        qs = super().get_queryset()
        city = self.request.query_params.get('city')
        state = self.request.query_params.get('state')
        if city:
            logger.info(f"Filtering by city: {city}")
            qs = qs.filter(city__iexact=city)
        if state:
            logger.info(f"Filtering by state: {state}")
            qs = qs.filter(state__iexact=state)
        logger.info(f"Final queryset count: {qs.count()}")
        return qs

    def get_object(self):
        """
        Retrieves a station, raising custom exceptions for inactive or missing stations.
        """
        logger.info(f"Attempting to get station with code: {self.kwargs.get('code')}")
        try:
            station = Station.all_objects.get(code=self.kwargs['code'])
            logger.info(f"Successfully retrieved station: {station.name} ({station.code})")
            return station
        except Station.DoesNotExist:
            logger.warning(f"Station with code {self.kwargs.get('code')} not found.")
            raise StationNotFoundException()

    @action(detail=True, methods=['post'], url_path='assign-master')
    def assign_master(self, request, code=None):
        logger.info(f"Attempting to assign master for station with code: {code}")
        station = self.get_object()
        serializer = AssignStationMasterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user_id = serializer.validated_data['user_id']
        user = get_object_or_404(User, id=user_id)
        logger.info(f"Attempting to validate user for assignment: {user.username} (ID: {user.id})")
        if not user.is_active:
            logger.warning(f"User {user.username} (ID: {user.id}) is not active. Cannot assign as station master.")
            raise NotFound(UserMessage.USER_NOT_FOUND)
        if user.role != 'station_master':
            logger.warning(f"User {user.username} (ID: {user.id}) does not have role=station_master")
            raise UnauthorizedAccessException()
        if hasattr(user, 'station') and user.station is not None and user.station != station:
            logger.warning(f"User {user.username} (ID: {user.id}) is already assigned as station master to station {user.station.name} ({user.station.code}).")
            raise StationMasterExistsException()
        if station.station_master and station.station_master != user:
            logger.warning(f"Station {station.name} ({station.code}) already has a different station master ({station.station_master.username}).")
            raise StationMasterExistsException()
        station.station_master = user
        station.save()
        logger.info(f"Successfully assigned station master for station {station.name} ({station.code}) to user {user.username} (ID: {user.id}).")
        return Response({'detail': 'Station master assigned successfully.'})

    def destroy(self, request, *args, **kwargs):
        code = kwargs.get('code')
        logger.info(f"Attempting to soft delete (deactivate) station with code: {code}")
        station = self.get_object()
        if not station.is_active:
            logger.warning(f"Station {station.name} ({station.code}) is already inactive.")
            raise StationNotFoundException()

        # Handle route edge merging for non-junction stations
        from routes.models import RouteEdge
        incoming_edges = RouteEdge.objects.filter(to_station=station, is_active=True)
        outgoing_edges = RouteEdge.objects.filter(from_station=station, is_active=True)
        if incoming_edges.count() == 1 and outgoing_edges.count() == 1:
            in_edge = incoming_edges.first()
            out_edge = outgoing_edges.first()
            # Deactivate both edges
            in_edge.is_active = False
            in_edge.save()
            out_edge.is_active = False
            out_edge.save()
            logger.info(f"Deactivated edges: {in_edge} and {out_edge} due to station removal.")
            # Create new edge bypassing the removed station
            RouteEdge.objects.create(
                from_station=in_edge.from_station,
                to_station=out_edge.to_station,
                distance=in_edge.distance + out_edge.distance,
                is_bidirectional=in_edge.is_bidirectional and out_edge.is_bidirectional,
                is_active=True
            )
            logger.info(f"Created new edge from {in_edge.from_station} to {out_edge.to_station} with distance {in_edge.distance + out_edge.distance}.")
        else:
            logger.info(f"Station {station.name} ({station.code}) is a junction or not a simple pass-through; no edge merging performed.")

        station.is_active = False
        station.save()
        logger.info(f"Successfully deactivated station {station.name} ({station.code}).")
        return Response(status=status.HTTP_204_NO_CONTENT)

    def create(self, request, *args, **kwargs):
        logger.info(f"Attempting to create station with data: {request.data}")
        code = request.data.get('code')
        name = request.data.get('name')
        # Check for any existing station with the same code or name
        if Station.all_objects.filter(code=code).exists():
            logger.warning(f"Station with code {code} already exists.")
            raise StationAlreadyExistsException()
        if Station.all_objects.filter(name=name).exists():
            logger.warning(f"Station with name {name} already exists.")
            raise StationAlreadyExistsException()
        return super().create(request, *args, **kwargs)
