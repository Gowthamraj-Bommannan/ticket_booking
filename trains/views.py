import logging
from datetime import datetime, timedelta
from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.permissions import BasePermission
from datetime import datetime, timedelta
from rest_framework.decorators import action
from stations.models import Station
from routes.models import RouteEdge
from utils.constants import RouteMessage
from django.http import Http404
import heapq
from .models import Train, TrainSchedule
from .serializers import (
    TrainSerializer,
    TrainCreateUpdateSerializer,
    TrainScheduleSerializer,
)
from utils.constants import TrainMessage
from exceptions.handlers import (
    TrainNotFoundException,
    TrainAlreadyExistsException,
    InvalidInput,
    NotFound,
    RouteStopsNotFoundException,
    ScheduleAlreadyExists,
    ScheduleNotFoundException,
)

logger = logging.getLogger("trains")


class IsAdminSuperUser(BasePermission):
    """
    Allows access only to admin users.
    """

    def has_permission(self, request, view):
        """
        Checks if the user has admin permissions.
        """
        return bool(
            request.user
            and request.user.is_authenticated
            and getattr(request.user, "role", None) == "admin"
        )


class TrainViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing trains.
    Supports CRUD operations and custom actions.
    """

    queryset = Train.objects.all()
    lookup_field = "train_number"

    def get_serializer_class(self):
        """
        Serializer for creation and updation of trains.
        """
        if self.action in ["create", "update", "partial_update"]:
            return TrainCreateUpdateSerializer
        return TrainSerializer

    def get_permissions(self):
        return [IsAdminSuperUser()]

    def get_queryset(self):
        qs = super().get_queryset()
        train_type = self.request.query_params.get("train_type")
        if train_type:
            qs = qs.filter(train_type=train_type)
        return qs

    def get_object(self):
        """
        Return the object if present else raises 404.
        """
        try:
            return super().get_object()
        except Http404:
            train_number = self.kwargs.get("train_number")
            if train_number:
                inactive_train = Train.all_objects.filter(
                    train_number=train_number, is_active=False
                ).first()
                if inactive_train:
                    raise TrainNotFoundException()
            raise TrainNotFoundException()

    def create(self, request, *args, **kwargs):
        logger.info(f"Attempting to create train with data: {request.data}")
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        validated_data = serializer.validated_data
        if "train_number" in validated_data:
            if Train.all_objects.filter(
                train_number=validated_data["train_number"]
            ).exists():
                raise TrainAlreadyExistsException()
        train = Train.objects.create(**validated_data)
        response_serializer = TrainSerializer(train)
        logger.info(f"Train created successfully: {train.train_number}")
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        logger.info(
            f"Attempting to update train {instance.train_number} with data: {request.data}"
        )
        serializer = self.get_serializer(
            instance, data=request.data, partial=kwargs.get("partial", False)
        )
        serializer.is_valid(raise_exception=True)
        validated_data = serializer.validated_data
        instance.name = validated_data.get("name", instance.name)
        instance.train_type = validated_data.get("train_type", instance.train_type)
        instance.save()
        response_serializer = TrainSerializer(instance)
        logger.info(f"Train updated successfully: {instance.train_number}")
        return Response(response_serializer.data)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        if not instance.is_active:
            raise TrainNotFoundException()
        instance.is_active = False
        instance.save()
        logger.info(
            f"Train soft-deleted (is_active set to False): {instance.train_number}"
        )
        return Response(
            {
                "detail": f"Train {instance.name} ({instance.train_number}) has been removed."
            },
            status=status.HTTP_204_NO_CONTENT,
        )


class TrainScheduleViewSet(viewsets.ModelViewSet):
    """
    Handles CRUD operations for TrainSchedule.
    Supports schedule creation, update, validation, and retrieval.
    Includes logic for pathfinding and conflict checking.
    """

    queryset = TrainSchedule.objects.all()
    serializer_class = TrainScheduleSerializer
    permission_classes = [IsAdminSuperUser]

    def create(self, request, *args, **kwargs):
        """
        Create a new schedule for a train with validations.
        Calculates stops, distances, timings, and checks for overlaps.
        Handles fast/local routes and bidirectional paths.
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        validated_data = serializer.validated_data

        try:
            route_template = validated_data["route_template"]
        except KeyError:
            logger.error("Route template not provided.")
            raise InvalidInput(TrainMessage.TRAIN_SCHEDULE_REQUIRED)
        except NotFound:
            logger.error("Train schedule not found.")
            raise NotFound(TrainMessage.TRAIN_SCHEDULE_NOT_FOUND)

        stops_codes = [code.strip().upper() for code in route_template.stops]
        if not stops_codes or len(stops_codes) < 2:
            logger.error("Route template does not have enough stops.")
            raise RouteStopsNotFoundException()

        stations = []
        for code in stops_codes:
            station = Station.objects.filter(code__iexact=code).first()
            if not station:
                logger.error(f"Station with code {code} not found.")
                raise RouteStopsNotFoundException(
                    f"Station with code {code} not found."
                )
            stations.append(station)

        # Determine if this is a fast train
        train = validated_data["train"]
        is_fast = (
            hasattr(route_template, "category")
            and getattr(route_template, "category", "").lower() == "fast"
        )
        distances = []
        if is_fast:
            # For each consecutive pair, find shortest path and sum distances
            for stop in range(len(stops_codes) - 1):
                code_a = stops_codes[stop]
                code_b = stops_codes[stop + 1]
                path, total_distance = self._find_shortest_path(code_a, code_b)
                if path is None:
                    logger.error(
                        f"No route found between {code_a} to {code_b} (fast train pathfinding)"
                    )
                    raise RouteStopsNotFoundException(
                        RouteMessage.ROUTE_NOT_FOUND_BETWEEN
                    )
                distances.append(total_distance)
        else:
            # Local: require direct edge
            from django.db.models import Q

            for stop in range(len(stops_codes) - 1):
                code_a = stops_codes[stop]
                code_b = stops_codes[stop + 1]
                edge = RouteEdge.objects.filter(
                    (
                        Q(
                            from_station__code__iexact=code_a,
                            to_station__code__iexact=code_b,
                        )
                        | Q(
                            from_station__code__iexact=code_b,
                            to_station__code__iexact=code_a,
                            is_bidirectional=True,
                        )
                    ),
                    is_active=True,
                ).first()
                if not edge:
                    logger.error(f"No route found between {code_a} to {code_b}")
                    raise RouteStopsNotFoundException(
                        RouteMessage.ROUTE_NOT_FOUND_BETWEEN
                    )
                distances.append(edge.distance)

        start_time = validated_data["start_time"]
        stops_with_time = self._generate_schedule_timings(
            stations, distances, start_time
        )

        # --- Overlap Validation with generated times ---
        from datetime import datetime

        new_start = start_time
        new_end = datetime.strptime(stops_with_time[-1]["arrival_time"], "%H:%M").time()
        new_days = set([d.strip() for d in validated_data["days_of_week"].split(",")])

        existing_schedules = TrainSchedule.objects.filter(
            train=validated_data["train"], is_active=True
        )

        for sched in existing_schedules:
            sched_days = set([d.strip() for d in sched.days_of_week.split(",")])
            if not (new_days & sched_days):
                continue  # No overlapping days

            sched_start = sched.start_time
            sched_end = None
            if sched.stops_with_time and len(sched.stops_with_time) > 0:
                sched_end = datetime.strptime(
                    sched.stops_with_time[-1]["arrival_time"], "%H:%M"
                ).time()
            else:
                continue  # skip if no stops

            # Check for overlap regardless of direction
            if new_start < sched_end and sched_start < new_end:
                logger.error("Schedule overlap detected for train.")
                raise ScheduleAlreadyExists(TrainMessage.TRAIN_SCHEDULE_OVERLAPS)
        # --- End Overlap Validation ---

        # --- Direction Alternation Validation ---
        # Find the latest schedule that ends before the new start time
        latest_prior_schedule = None
        for sched in existing_schedules.order_by("start_time"):
            if sched.stops_with_time and len(sched.stops_with_time) > 0:
                sched_end = datetime.strptime(
                    sched.stops_with_time[-1]["arrival_time"], "%H:%M"
                ).time()
                if sched_end <= new_start:
                    latest_prior_schedule = sched
        if latest_prior_schedule:
            prev_direction = latest_prior_schedule.direction
            new_direction = validated_data["direction"]
            prev_last_station_code = (
                latest_prior_schedule.route_template.stops[-1].strip().upper()
            )
            new_first_station_code = route_template.stops[0].strip().upper()
            if prev_direction == new_direction:
                logger.error(
                    "Train cannot have two consecutive schedules in the same direction without a return trip."
                )
                raise ScheduleAlreadyExists(TrainMessage.SCHEDULE_DIRECTION_NOT_BE_SAME)
            if prev_last_station_code != new_first_station_code:
                logger.error(
                    "Train's new schedule does not start from the previous journey's end station."
                )
                raise ScheduleAlreadyExists(
                    TrainMessage.TRAIN_SCHEDULE_MUST_BE_DIFFERENT
                )
        schedule = TrainSchedule.objects.create(
            train=validated_data["train"],
            route_template=route_template,
            days_of_week=validated_data["days_of_week"],
            start_time=start_time,
            direction=validated_data["direction"],
            stops_with_time=stops_with_time,
            is_active=validated_data.get("is_active", True),
        )
        logger.info(f"Train schedule added successfully: {schedule.id}")
        response = self.get_serializer(schedule)
        return Response(response.data, status=status.HTTP_201_CREATED)

    def _find_shortest_path(self, code_a, code_b):
        """
        Dijkstra's algorithm to find shortest path and total distance between two stations.
        Returns (path, total_distance) or (None, None) if no path exists.
        """
        # Build graph
        edges = RouteEdge.objects.filter(is_active=True)
        graph = {}
        for edge in edges:
            graph.setdefault(edge.from_station.code.upper(), []).append(
                (edge.to_station.code.upper(), edge.distance)
            )
            if edge.is_bidirectional:
                graph.setdefault(edge.to_station.code.upper(), []).append(
                    (edge.from_station.code.upper(), edge.distance)
                )
        # Dijkstra
        queue = [(0, code_a, [code_a])]
        visited = set()
        while queue:
            dist, current, path = heapq.heappop(queue)
            if current == code_b:
                return path, dist
            if current in visited:
                continue
            visited.add(current)
            for neighbor, weight in graph.get(current, []):
                if neighbor not in visited:
                    heapq.heappush(queue, (dist + weight, neighbor, path + [neighbor]))
        return None, None

    @staticmethod
    def _generate_schedule_timings(
        stations, distances, start_time, speed=35, halt_min=1
    ):
        """
        Generate arrival and departure times for each station in the route.
        - For the first station: only departure_time is set, arrival_time is None.
        - For the last station: only arrival_time is set, departure_time is None.
        - For in-between stations: both are set.
        """
        result = []
        current_time = datetime.combine(datetime.today(), start_time)
        for idx, station in enumerate(stations):
            if idx == 0:
                # First station: only departure_time
                arrival = None
                departure = current_time
            else:
                # Travel from previous station
                travel_mins = (distances[idx - 1] / speed) * 60
                arrival = departure + timedelta(minutes=travel_mins)
                if idx == len(stations) - 1:
                    # Last station: only arrival_time
                    departure = None
                else:
                    departure = arrival + timedelta(minutes=halt_min)
            result.append(
                {
                    "station_code": station.code,
                    "arrival_time": arrival.strftime("%H:%M") if arrival else None,
                    "departure_time": (
                        departure.strftime("%H:%M") if departure else None
                    ),
                }
            )
        return result

    def update(self, request, *args, **kwargs):
        """
        Updates an existing train schedule with all validations.
        Ensures no overlaps or invalid directional flows.
        """
        instance = self.get_object()
        partial = kwargs.get("partial", False)
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        validated_data = serializer.validated_data

        try:
            route_template = validated_data["route_template"]
        except KeyError:
            logger.error("Route template not provided.")
            raise InvalidInput(TrainMessage.TRAIN_SCHEDULE_REQUIRED)
        except NotFound:
            logger.error("Train schedule not found.")
            raise NotFound(TrainMessage.TRAIN_SCHEDULE_NOT_FOUND)

        stops_codes = [code.strip().upper() for code in route_template.stops]
        if not stops_codes or len(stops_codes) < 2:
            logger.error("Route template does not have enough stops.")
            raise RouteStopsNotFoundException()

        stations = []
        for code in stops_codes:
            station = Station.objects.filter(code__iexact=code).first()
            if not station:
                logger.error(f"Station with code {code} not found.")
                raise RouteStopsNotFoundException(
                    f"Station with code {code} not found."
                )
            stations.append(station)

        from django.db.models import Q

        distances = []
        for stop in range(len(stops_codes) - 1):
            code_a = stops_codes[stop]
            code_b = stops_codes[stop + 1]
            edge = RouteEdge.objects.filter(
                (
                    Q(
                        from_station__code__iexact=code_a,
                        to_station__code__iexact=code_b,
                    )
                    | Q(
                        from_station__code__iexact=code_b,
                        to_station__code__iexact=code_a,
                        is_bidirectional=True,
                    )
                ),
                is_active=True,
            ).first()
            if not edge:
                logger.error(f"No route found between {code_a} to {code_b}")
                raise RouteStopsNotFoundException(RouteMessage.ROUTE_NOT_FOUND_BETWEEN)
            distances.append(edge.distance)

        start_time = validated_data["start_time"]
        stops_with_time = self._generate_schedule_timings(
            stations, distances, start_time
        )

        # --- Overlap Validation with generated times ---
        from datetime import datetime

        new_start = start_time
        new_end = datetime.strptime(stops_with_time[-1]["arrival_time"], "%H:%M").time()
        new_days = set([d.strip() for d in validated_data["days_of_week"].split(",")])

        existing_schedules = TrainSchedule.objects.filter(
            train=validated_data["train"], is_active=True
        ).exclude(pk=instance.pk)

        for sched in existing_schedules:
            sched_days = set([d.strip() for d in sched.days_of_week.split(",")])
            if not (new_days & sched_days):
                continue  # No overlapping days

            sched_start = sched.start_time
            sched_end = None
            if sched.stops_with_time and len(sched.stops_with_time) > 0:
                sched_end = datetime.strptime(
                    sched.stops_with_time[-1]["arrival_time"], "%H:%M"
                ).time()
            else:
                continue  # skip if no stops

            # Check for overlap regardless of direction
            if new_start < sched_end and sched_start < new_end:
                logger.error("Schedule overlap detected for train.")
                raise ScheduleAlreadyExists(TrainMessage.TRAIN_SCHEDULE_OVERLAPS)
        # --- End Overlap Validation ---

        # --- Direction Alternation Validation ---
        # Find the latest schedule that ends before the new start time
        latest_prior_schedule = None
        for sched in existing_schedules.order_by("start_time"):
            if sched.stops_with_time and len(sched.stops_with_time) > 0:
                sched_end = datetime.strptime(
                    sched.stops_with_time[-1]["arrival_time"], "%H:%M"
                ).time()
                if sched_end <= new_start:
                    latest_prior_schedule = sched
        if latest_prior_schedule:
            prev_direction = latest_prior_schedule.direction
            new_direction = validated_data["direction"]
            prev_last_station_code = (
                latest_prior_schedule.route_template.stops[-1].strip().upper()
            )
            new_first_station_code = route_template.stops[0].strip().upper()
            if prev_direction == new_direction:
                logger.error(
                    "Train cannot have two consecutive schedules in the same direction without a return trip."
                )
                raise ScheduleAlreadyExists(TrainMessage.SCHEDULE_DIRECTION_NOT_BE_SAME)
            # New validation: ensure the new trip starts where the last one ended
            if prev_last_station_code != new_first_station_code:
                logger.error(
                    "Train's new schedule does not start from the previous journey's end station."
                )
                raise ScheduleAlreadyExists(
                    TrainMessage.TRAIN_SCHEDULE_MUST_BE_DIFFERENT
                )
        # --- End Direction Alternation Validation ---

        # Update the instance fields
        instance.route_template = route_template
        instance.days_of_week = validated_data["days_of_week"]
        instance.start_time = start_time
        instance.direction = validated_data["direction"]
        instance.stops_with_time = stops_with_time
        instance.is_active = validated_data.get("is_active", instance.is_active)
        instance.save()

        logger.info(f"Train schedule updated successfully: {instance.id}")
        response = self.get_serializer(instance)
        return Response(response.data)

    def destroy(self, request, *args, **kwargs):
        """
        Soft deletes a train schedule by marking it inactive.
        Validates if already inactive before deletion.
        """
        instance = self.get_object()
        if not instance.is_active:
            logger.error(f"Train schedule {instance.id} is already inactive.")
            raise ScheduleNotFoundException()
        instance.is_active = False
        instance.save()
        logger.info(f"Train schedule {instance.id} deleted successfully.")
        return Response(
            {"detail": f"Train schedule {instance.id} has been deleted successfully."},
            status=status.HTTP_204_NO_CONTENT,
        )

    @action(detail=False, methods=["get"], url_path="by-train/(?P<train_number>[^/]+)")
    def schedule_by_train(self, request, train_number=None):
        """
        Returns all active schedules for a given train number.
        Raises exception if the train is not found.
        """
        train = Train.objects.filter(train_number=train_number).first()
        if not train:
            logger.error(f"train not found with number {train_number}")
            raise TrainNotFoundException()
        schedules = self.get_queryset().filter(train=train)
        serialzer = self.get_serializer(schedules, many=True)
        return Response(serialzer.data, status=status.HTTP_200_OK)
