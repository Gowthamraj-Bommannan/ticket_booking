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
    StationNotFoundException, StationAlreadyInactiveException, 
    StationAlreadyActiveException, StationInactiveException
)
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
            station = super().get_object()
            logger.info(f"Successfully retrieved station: {station.name} ({station.code})")
            return station
        except Http404:
            logger.warning(f"Station with code {self.kwargs.get('code')} not found.")
            # Check if station exists but is inactive
            code = self.kwargs.get('code')
            if code:
                inactive_station = Station.all_objects.filter(code=code, is_active=False).first()
                if inactive_station:
                    logger.warning(f"Station {inactive_station.name} ({inactive_station.code}) is inactive.")
                    raise StationInactiveException()
            logger.error(f"Station with code {code} not found and is not inactive.")
            raise StationNotFoundException()

    @action(detail=True, methods=['post'], url_path='assign-master')
    def assign_master(self, request, code=None):
        """
        Assigns a user as the station master for a station.
        """
        logger.info(f"Attempting to assign master for station with code: {code}")
        station = self.get_object()
        serializer = AssignStationMasterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user_id = serializer.validated_data['user_id']
        user = get_object_or_404(User, id=user_id)
        logger.info(f"Attempting to validate user for assignment: {user.username} (ID: {user.id})")
        # Validation: is_active first, then role, is_staff, not already assigned
        if not user.is_active:
            logger.warning(f"User {user.username} (ID: {user.id}) is not active. Cannot assign as station master.")
            return Response({'detail': 'User must be active (is_active=True).'}, status=400)
        if user.role != 'station_master':
            logger.warning(f"User {user.username} (ID: {user.id}) does not have role=station_master. Cannot assign as station master.")
            return Response({'detail': 'User must have role=station_master.'}, status=400)
        if hasattr(user, 'station') and user.station is not None and user.station != station:
            logger.warning(f"User {user.username} (ID: {user.id}) is already assigned as station master to station {user.station.name} ({user.station.code}). Cannot re-assign.")
            return Response({'detail': 'User is already assigned as station master to another station.'}, status=400)
        if station.station_master and station.station_master != user:
            logger.warning(f"Station {station.name} ({station.code}) already has a different station master ({station.station_master.username}). Cannot re-assign.")
            return Response({'detail': 'Station already has a different station master.'}, status=400)
        station.station_master = user
        station.save()
        logger.info(f"Successfully assigned station master for station {station.name} ({station.code}) to user {user.username} (ID: {user.id}).")
        return Response({'detail': 'Station master assigned successfully.'})

    @action(detail=True, methods=['delete'], url_path='remove')
    def deactivate(self, request, code=None):
        """
        Soft deletes a station by setting is_active=False.
        """
        logger.info(f"Attempting to deactivate station with code: {code}")
        station = get_object_or_404(Station.all_objects, code=code)
        
        if not station.is_active:
            logger.warning(f"Station {station.name} ({station.code}) is already inactive. Cannot re-deactivate.")
            raise StationAlreadyInactiveException()
        
        station.is_active = False
        station.save()
        logger.info(f"Successfully deactivated station {station.name} ({station.code}).")
        
        return Response({
            'detail': f'Station {station.name} ({station.code}) has been deactivated.'
        }, status=status.HTTP_200_OK)
    
    @action(detail=True, methods=['post'], url_path='activate')
    def activate(self, request, code=None):
        """
        Reactivates a station by setting is_active=True.
        """
        logger.info(f"Attempting to activate station with code: {code}")
        station = get_object_or_404(Station.all_objects, code=code)
        
        if station.is_active:
            logger.warning(f"Station {station.name} ({station.code}) is already active. Cannot re-activate.")
            raise StationAlreadyActiveException()
        
        station.is_active = True
        station.save()
        logger.info(f"Successfully activated station {station.name} ({station.code}).")
        
        return Response({
            'detail': f'Station {station.name} ({station.code}) has been activated.'
        }, status=status.HTTP_200_OK)
