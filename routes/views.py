from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.permissions import BasePermission
from .models import RouteEdge, RouteTemplate
from stations.models import Station
from .serializers import RouteEdgeSerializer, RouteTemplateSerializer
from rest_framework.decorators import action
from exceptions.handlers import (RoutePermissionDeniedException, 
                    StationNotFoundException, RouteInvalidInputException,
                    RouteFromAndToSameException, RouteInvalidDistanceException,
                    RouteAlreadyExistsException, RouteStopsNotFoundException)
from utils.constants import RouteMessage, StationMessage
import logging
import heapq

logger = logging.getLogger("routes")

class IsAdminSuperUser(BasePermission):
    """
    Allows access to admin users.
    """
    def has_permission(self, request, view):
        logger.info(f"Checking IsAdminSuperUser permission for user: {request.user.username}")
        permission_granted = bool(
            request.user and 
            request.user.is_authenticated and
            request.user.role == 'admin'
        )
        logger.info(f"IsAdminSuperUser permission granted: {permission_granted}")
        return permission_granted


class RouteEdgeViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing route edges.
    Supports CRUD operations and custom actions.
    """
    queryset = RouteEdge.objects.filter(is_active=True)
    serializer_class = RouteEdgeSerializer

    def get_queryset(self):
        """
        Returns the queryset of active route edges.
        """
        qs = super().get_queryset()
        return qs.filter(is_active=True)

    def create(self, request, *args, **kwargs):
        """
        Creates a new route edge.
        Validates and processes route edge data.
        """
        if not IsAdminSuperUser().has_permission(request, self):
            logger.error("You do not have permission to create route edges")
            raise RoutePermissionDeniedException(RouteMessage
                                                 .ROUTE_EDGE_PERMISSION_DENIED)
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        logger.info(f"Route edge created: {serializer.data} by {request.user.username}")
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def update(self, request, *args, **kwargs):
        """
        Updates a route edge.
        Validates and processes route edge data.
        """
        if not IsAdminSuperUser().has_permission(request, self):
            logger.error("You do not have permission to update route edges")
            raise RoutePermissionDeniedException(RouteMessage
                                                 .ROUTE_EDGE_PERMISSION_DENIED)
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        logger.info(f"Route edge updated: {serializer.data} by {request.user.username}")
        return Response(serializer.data)

    def destroy(self, request, *args, **kwargs):
        """
        Deletes a route edge.
        Marks the edge as inactive.
        """
        if not IsAdminSuperUser().has_permission(request, self):
            logger.warn("You do not have permission to delete route edges")
            raise RoutePermissionDeniedException(RouteMessage
                                                 .ROUTE_EDGE_PERMISSION_DENIED)
        instance = self.get_object()
        instance.is_active = False
        instance.save()
        logger.info(f"route removed successfully by {request.user.username}.")
        return Response(status=status.HTTP_204_NO_CONTENT)
    
    @action(detail=False, methods=['post'], url_path='add-between')
    def add_between(self, request):
        """
        Adds a new route edge between two stations.
        Validates and processes route edge data.
        """
        self._check_admin_permission(request.user)
        from_station, to_station, distance, is_bidirectional = self._validate_add_between_input(request.data)
        self._check_existing_edges(from_station, to_station, is_bidirectional)
        split_edges = self._split_existing_edge(from_station, to_station, distance, is_bidirectional)
        if split_edges:
            serializer1 = RouteEdgeSerializer(split_edges[0])
            serializer2 = RouteEdgeSerializer(split_edges[1])
            return Response(
                {
                    "detail": "Edge split and new edges created.",
                    "new_edges": [serializer1.data, serializer2.data]
                },
                status=status.HTTP_201_CREATED
            )
        new_edge = self._create_new_edge(from_station, to_station, distance, is_bidirectional)
        serializer = RouteEdgeSerializer(new_edge)
        logger.info(f"New stop added successfully by {request.user.username}.")
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    
    def _check_admin_permission(self, user):
        """
        Checks if the user has admin permissions.
        Raises error if not authorized.
        """
        if not (user and user.is_authenticated and getattr(user, 'role', None) == 'admin'):
            logger.warning(f"User {getattr(user, 'username', 'Anonymous')} is not authorized to add route edges.")
            raise RoutePermissionDeniedException("Only admin users can add route edges.")

    def _validate_add_between_input(self, data):
        """
        Validates the input data for adding a route edge.
        Raises error if invalid.
        """
        from_code = data.get('from_station')
        to_code = data.get('to_station')
        distance = data.get('distance')
        is_bidirectional = data.get('is_bidirectional', True)
        if not from_code or not to_code or distance is None:
            logger.error("Missing required fields: from_station, to_station, or distance.")
            raise RouteInvalidDistanceException()
        if from_code == to_code:
            logger.error("from_station and to_station must be different.")
            raise RouteFromAndToSameException()
        try:
            from_station = Station.objects.get(code=from_code)
            to_station = Station.objects.get(code=to_code)
        except Station.DoesNotExist:
            logger.error(f"Station with code '{from_code}' or '{to_code}' not found.")
            raise StationNotFoundException(f"Station with code '{from_code}' or '{to_code}' not found.")
        try:
            distance = int(distance)
        except (TypeError, ValueError):
            logger.error("Distance must be a positive integer.")
            raise RouteInvalidDistanceException("Distance must be a positive integer.")
        if distance <= 0:
            logger.error("Distance must be a positive integer.")
            raise RouteInvalidDistanceException("Distance must be a positive integer.")
        return from_station, to_station, distance, is_bidirectional

    def _check_existing_edges(self, from_station, to_station, is_bidirectional):
        """
        Checks if an edge already exists between the two stations.
        Raises error if it does.
        """
        if is_bidirectional:
            if RouteEdge.objects.filter(
                from_station=from_station, to_station=to_station, is_bidirectional=True, is_active=True
            ).exists() or RouteEdge.objects.filter(
                from_station=to_station, to_station=from_station, is_bidirectional=True, is_active=True
            ).exists():
                logger.error("A bidirectional edge between these stations already exists.")
                raise RouteAlreadyExistsException("A bidirectional edge between these stations already exists.")
        else:
            if RouteEdge.objects.filter(
                from_station=from_station, to_station=to_station, is_bidirectional=False, is_active=True
            ).exists():
                logger.error("A unidirectional edge in this direction already exists.")
                raise RouteAlreadyExistsException("A unidirectional edge in this direction already exists.")

    def _split_existing_edge(self, from_station, to_station, distance, is_bidirectional):
        """
        Splits an existing edge into two new edges.
        Raises error if it does.
        """
        existing_edge = RouteEdge.objects.filter(
            from_station=from_station, is_active=True
        ).exclude(to_station=to_station).first()
        if existing_edge and existing_edge.to_station != to_station:
            if existing_edge.distance > distance:
                existing_edge.is_active = False
                existing_edge.save()
                logger.info(f"Deactivated existing edge: {existing_edge}")
                new_edge1 = RouteEdge.objects.create(
                    from_station=from_station,
                    to_station=to_station,
                    distance=distance,
                    is_bidirectional=is_bidirectional,
                    is_active=True
                )
                new_edge2 = RouteEdge.objects.create(
                    from_station=to_station,
                    to_station=existing_edge.to_station,
                    distance=existing_edge.distance - distance,
                    is_bidirectional=is_bidirectional,
                    is_active=True
                )
                logger.info(f"Created new split edges: {new_edge1} and {new_edge2}")
                return [new_edge1, new_edge2]
        return None

    def _create_new_edge(self, from_station, to_station, distance, is_bidirectional):
        """
        Creates a new edge between two stations.
        Raises error if it does.
        """
        new_edge = RouteEdge.objects.create(
            from_station=from_station,
            to_station=to_station,
            distance=distance,
            is_bidirectional=is_bidirectional,
            is_active=True
        )
        logger.info(f"Created new edge: {new_edge}")
        return new_edge
    
class RouteTemplateViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing route templates.
    Supports CRUD operations and custom actions.
    """
    queryset = RouteTemplate.objects.all()
    serializer_class = RouteTemplateSerializer
    permission_classes = [IsAdminSuperUser]

    def create(self, request, *args, **kwargs):
        """
        Creates a new route template.
        Validates and processes route template data.
        """
        logger.info(f"Attempting to create route template with data: {request.data}")
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        validated_data = serializer.validated_data
        category = validated_data['category']
        
        if category.lower() == 'local':
            
            stops = self._get_stops_for_route(validated_data['from_station'],
                                              validated_data['to_station'])
            stop_codes = [station.code for station in stops]
        else:
            stop_codes = validated_data['stops']
            if len(stop_codes) < 3:
                logger.warn("Train should have atleast one stop.(except from and to)")
                raise RouteStopsNotFoundException()
        template = serializer.save(stops=stop_codes)
        template.stops = stop_codes
        template.save()
        logger.info(f"Computed stops for template: {stop_codes}")
        response_data = serializer.data
        response_data['stops'] = stop_codes
        return Response(response_data, status=status.HTTP_201_CREATED)
    
    def _get_stops_for_route(self, from_station, to_station):
        """
        Computes the stops for a route between two stations.
        Uses Dijkstra's algorithm to find the shortest path.
        Returns a list of Station objects in the order of the route.
        """
        edges = RouteEdge.objects.filter(is_active=True)
        graph = {}
        for edge in edges:
            graph.setdefault(edge.from_station_id, []).append((edge.to_station_id, edge.distance))
            if edge.is_bidirectional:
                graph.setdefault(edge.to_station_id, []).append((edge.from_station_id, edge.distance))
        queue = [(0, from_station.id, [from_station.id])]
        visited = set()
        while queue:
            dist, current, path = heapq.heappop(queue)
            if current == to_station.id:
                # Return list of Station objects in order
                stations = Station.objects.filter(id__in=path)
                # Preserve order
                station_map = {s.id: s for s in stations}
                return [station_map[pid] for pid in path]
            if current in visited:
                continue
            visited.add(current)
            for neighbor, weight in graph.get(current, []):
                if neighbor not in visited:
                    heapq.heappush(queue, (dist + weight, neighbor, path + [neighbor]))
        return []
