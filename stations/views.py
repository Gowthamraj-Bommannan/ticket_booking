from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import Station
from django.db.models import Q
from .serializers import StationSerializer, AssignStationMasterSerializer
from exceptions.handlers import (
    NotFoundException,
    AlreadyExistsException,
)
from routes.models import RouteEdge
from utils.permission_helpers import DynamicPermissionMixin
from utils.queryset_helpers import FilterableQuerysetMixin
from utils.validators import StationValidators
from utils.constants import StationMessage
import logging

logger = logging.getLogger("stations")

class StationViewSet(DynamicPermissionMixin, FilterableQuerysetMixin,
                     viewsets.ModelViewSet):
    """
    Provides CRUD and soft delete endpoints for stations.
    Uses centralized validators for consistency and reduced code duplication.
    """

    queryset = Station.objects.all()
    serializer_class = StationSerializer
    lookup_field = "code"
    filter_fields = ["city", "state"]

    def get_queryset(self):
        """
        Returns the queryset of stations, filtered by city/state if provided.
        Optimized with select_related to prevent N+1 queries.
        """
        logger.info("Getting queryset for StationViewSet")
        qs = super().get_queryset().select_related('station_master')
        logger.info(f"Final queryset count: {qs.count()}")
        return qs

    def get_object(self):
        """
        Retrieves a station, raising custom exceptions for inactive or missing stations.
        Optimized with select_related to prevent additional queries.
        """
        logger.info(f"Attempting to get station with code: {self.kwargs.get('code')}")
        try:
            station = Station.all_objects.select_related('station_master').get(code=self.kwargs["code"])
            logger.info(
                f"Successfully retrieved station: {station.name} ({station.code})"
            )
            return station
        except Station.DoesNotExist:
            logger.warning(f"Station with code {self.kwargs.get('code')} not found.")
            raise NotFoundException(StationMessage.STATION_NOT_FOUND)

    @action(detail=True, methods=["post"], url_path="assign-master")
    def assign_master(self, request, code=None):
        """
        Assigns a station master to a station.
        Validates and processes station master data.
        Uses centralized validators for consistency.
        """
        logger.info(f"Attempting to assign master for station with code: {code}")
        station = self.get_object()
        
        # Validate station is active for assignment
        StationValidators.validate_station_active_for_operation(station, "assign master to")
        
        serializer = AssignStationMasterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user_id = serializer.validated_data["user_id"]
        
        # Use centralized validator for station master assignment
        try:
            user = StationValidators.validate_station_master_assignment(user_id, station)
        except Exception as e:
            logger.warning(f"Station master assignment validation failed: {str(e)}")
            raise AlreadyExistsException(str(e))
        
        logger.info(
            f"Attempting to validate user for assignment: {user.username} (ID: {user.id})"
        )
        
        station.station_master = user
        station.save()
        logger.info(
            f"Successfully assigned station master for station {station.name} ({station.code}) to user {user.username} (ID: {user.id})."
        )
        return Response({"detail": "Station master assigned successfully."})

    def destroy(self, request, *args, **kwargs):
        """
        Soft deletes a station.
        Merges route edges if the station is a junction.
        Optimized to reduce database hits and uses centralized validators.
        """
        code = kwargs.get("code")
        logger.info(f"Attempting to soft delete (deactivate) station with code: {code}")
        station = self.get_object()
        
        # Validate station is active for deletion
        StationValidators.validate_station_for_deletion(station)

        # Single query to get all related edges
        related_edges = RouteEdge.objects.filter(
            Q(from_station=station) | Q(to_station=station),
            is_active=True
        ).select_related('from_station', 'to_station')
        
        incoming_edges = [edge for edge in related_edges if edge.to_station == station]
        outgoing_edges = [edge for edge in related_edges if edge.from_station == station]
        
        if len(incoming_edges) == 1 and len(outgoing_edges) == 1:
            in_edge = incoming_edges[0]
            out_edge = outgoing_edges[0]
            
            # Bulk update to deactivate edges
            edge_ids = [in_edge.id, out_edge.id]
            RouteEdge.objects.filter(id__in=edge_ids).update(is_active=False)
            
            logger.info(
                f"Deactivated edges: {in_edge} and {out_edge} due to station removal."
            )
            
            # Create new edge bypassing the removed station
            RouteEdge.objects.create(
                from_station=in_edge.from_station,
                to_station=out_edge.to_station,
                distance=in_edge.distance + out_edge.distance,
                is_bidirectional=in_edge.is_bidirectional and out_edge.is_bidirectional,
                is_active=True,
            )
            logger.info(
                f"Created new edge from {in_edge.from_station} to "
                f"{out_edge.to_station} with distance"
                f"{in_edge.distance + out_edge.distance}."
            )
        else:
            logger.info(
                f"Station {station.name} ({station.code}) is a junction or not a simple pass-through."
            )

        station.is_active = False
        station.save()
        logger.info(
            f"{station.name} ({station.code}) station deleted successfully."
        )
        return Response(status=status.HTTP_204_NO_CONTENT)

    def create(self, request, *args, **kwargs):
        """
        Creates a new station.
        Validates and processes station data.
        Optimized to remove redundant validation queries.
        """
        logger.info(f"Attempting to create station with data: {request.data}")
        # Model validation in full_clean() already handles duplicate checks
        return super().create(request, *args, **kwargs)
