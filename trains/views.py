import logging
from datetime import datetime
from rest_framework import viewsets, status
from rest_framework.response import Response
from datetime import datetime
from rest_framework.decorators import action
from datetime import datetime
from utils.constants import RouteMessage
from django.http import Http404
from .models import Train, TrainSchedule
from .serializers import (
    TrainSerializer,
    TrainCreateUpdateSerializer,
    TrainScheduleSerializer,
)
from utils.constants import TrainMessage
from utils.permission_helpers import AdminOnlyPermissionMixin
from utils.queryset_helpers import FilterableQuerysetMixin
from utils.validators import TrainValidators
from utils.train_helpers import TrainPathfindingHelpers, TrainScheduleHelpers
from exceptions.handlers import (
    InvalidInputException,
    NotFoundException,
)

logger = logging.getLogger("trains")


class TrainViewSet(AdminOnlyPermissionMixin, FilterableQuerysetMixin, viewsets.ModelViewSet):
    """
    ViewSet for managing trains.
    Supports CRUD operations and custom actions.
    """

    queryset = Train.objects.all()
    lookup_field = "train_number"
    filter_fields = ["train_type"]  # Fields to filter by query parameters

    def get_serializer_class(self):
        """
        Serializer for creation and updation of trains.
        """
        if self.action in ["create", "update", "partial_update"]:
            return TrainCreateUpdateSerializer
        return TrainSerializer

    def get_object(self):
        """
        Return the object if present else raises 404.
        Optimized to use single query with select_related.
        """
        try:
            return super().get_object()
        except Http404:
            train_number = self.kwargs.get("train_number")
            if train_number:
                # Single query to check for inactive train
                inactive_train = Train.all_objects.filter(
                    train_number=train_number, is_active=False
                ).first()
                if inactive_train:
                    raise NotFoundException(TrainMessage.TRAIN_NOT_FOUND)
            raise NotFoundException(TrainMessage.TRAIN_NOT_FOUND)

    def create(self, request, *args, **kwargs):
        """
        Creates a new train with validations.
        Optimized to reduce database hits.
        """
        logger.info(f"Attempting to create train with data: {request.data}")
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        validated_data = serializer.validated_data
        
        # Validation is handled in serializer, no additional DB hits needed
        train = Train.objects.create(**validated_data)
        response_serializer = TrainSerializer(train)
        logger.info(f"Train created successfully: {train.train_number}")
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)

    def update(self, request, *args, **kwargs):
        """
        Updates an existing train with validations.
        Optimized to reduce database hits.
        """
        instance = self.get_object()
        logger.info(
            f"Attempting to update train {instance.train_number} with data: {request.data}"
        )
        serializer = self.get_serializer(
            instance, data=request.data, partial=kwargs.get("partial", False)
        )
        serializer.is_valid(raise_exception=True)
        validated_data = serializer.validated_data
        
        # Update fields directly to avoid additional queries
        instance.name = validated_data.get("name", instance.name)
        instance.train_type = validated_data.get("train_type", instance.train_type)
        instance.save()
        
        response_serializer = TrainSerializer(instance)
        logger.info(f"Train updated successfully: {instance.train_number}")
        return Response(response_serializer.data)

    def destroy(self, request, *args, **kwargs):
        """
        Deletes a train by marking it inactive.
        Optimized to use single query.
        """
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


class TrainScheduleViewSet(AdminOnlyPermissionMixin, viewsets.ModelViewSet):
    """
    Handles CRUD operations for TrainSchedule.
    Supports schedule creation, update, validation, and retrieval.
    Includes logic for pathfinding and conflict checking.
    """

    queryset = TrainSchedule.objects.all()
    serializer_class = TrainScheduleSerializer

    def create(self, request, *args, **kwargs):
        """
        Create a new schedule for a train with validations.
        Optimized to use centralized helpers and reduce database hits.
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        validated_data = serializer.validated_data
        
        # Process route template and validate stops using centralized helpers
        route_template, stations, distances = self._process_route_template(validated_data)
        
        # Generate schedule timings using centralized helper
        start_time = validated_data["start_time"]
        stops_with_time = TrainScheduleHelpers.generate_schedule_timings(
            stations, distances, start_time
        )
        
        # Validate schedule conflicts using centralized helper
        new_end = datetime.strptime(stops_with_time[-1]["arrival_time"], "%H:%M").time()
        new_days = set([d.strip() for d in validated_data["days_of_week"].split(",")])
        TrainScheduleHelpers.validate_schedule_conflicts(
            validated_data["train"], start_time, new_end, new_days, exclude_instance=None
        )
        
        # Validate direction alternation using centralized helper
        TrainScheduleHelpers.validate_direction_alternation(
            validated_data["train"], start_time, validated_data["direction"], route_template, exclude_instance=None
        )
        
        # Create schedule
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

    def update(self, request, *args, **kwargs):
        """
        Updates an existing train schedule with all validations.
        Optimized to use centralized helpers and reduce database hits.
        """
        instance = self.get_object()
        partial = kwargs.get("partial", False)
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        validated_data = serializer.validated_data
        
        # Process route template and validate stops using centralized helpers
        route_template, stations, distances = self._process_route_template(validated_data)
        
        # Generate schedule timings using centralized helper
        start_time = validated_data["start_time"]
        stops_with_time = TrainScheduleHelpers.generate_schedule_timings(
            stations, distances, start_time
        )
        
        # Validate schedule conflicts using centralized helper
        new_end = datetime.strptime(stops_with_time[-1]["arrival_time"], "%H:%M").time()
        new_days = set([d.strip() for d in validated_data["days_of_week"].split(",")])
        TrainScheduleHelpers.validate_schedule_conflicts(
            validated_data["train"], start_time, new_end, new_days, exclude_instance=instance
        )
        
        # Validate direction alternation using centralized helper
        TrainScheduleHelpers.validate_direction_alternation(
            validated_data["train"], start_time, validated_data["direction"], route_template, exclude_instance=instance
        )
        
        # Update instance using centralized helper
        self._update_schedule_instance(instance, validated_data, route_template, start_time, stops_with_time)
        logger.info(f"Train schedule updated successfully: {instance.id}")
        response = self.get_serializer(instance)
        return Response(response.data)

    def _process_route_template(self, validated_data):
        """
        Process route template and validate stops using centralized helpers.
        Returns (route_template, stations, distances)
        """
        try:
            route_template = validated_data["route_template"]
        except KeyError:
            logger.error("Route template not provided.")
            raise InvalidInputException()
        except NotFoundException:
            logger.error("Train schedule not found.")
            raise NotFoundException(TrainMessage.TRAIN_SCHEDULE_NOT_FOUND)

        stops_codes = [code.strip().upper() for code in route_template.stops]
        if not stops_codes or len(stops_codes) < 2:
            logger.error("Route template does not have enough stops.")
            raise NotFoundException(RouteMessage.ROUTE_TEMPLATE_NOT_ENOUGH_STOPS)

        # Use centralized helper for station validation (single query)
        stations = TrainValidators.validate_stations_exist(stops_codes)

        # Use centralized helper for distance calculation
        distances = TrainPathfindingHelpers.calculate_distances(route_template, stops_codes)
        
        return route_template, stations, distances

    def _update_schedule_instance(self, instance, validated_data, route_template, start_time, stops_with_time):
        """
        Update the schedule instance with new data.
        """
        instance.route_template = route_template
        instance.days_of_week = validated_data["days_of_week"]
        instance.start_time = start_time
        instance.direction = validated_data["direction"]
        instance.stops_with_time = stops_with_time
        instance.is_active = validated_data.get("is_active", instance.is_active)
        instance.save()

    def destroy(self, request, *args, **kwargs):
        """
        Soft deletes a train schedule by marking it inactive.
        Validates if already inactive before deletion.
        """
        instance = self.get_object()
        if not instance.is_active:
            logger.error(f"Train schedule {instance.id} is already inactive.")
            raise NotFoundException(TrainMessage.TRAIN_SCHEDULE_NOT_FOUND)
        instance.is_active = False
        instance.save()
        logger.info(f"Train schedule {instance.id} deleted successfully.")
        return Response(
            {"detail": f"Train schedule {instance.id} has been deleted successfully."},
            status=status.HTTP_204_NO_CONTENT,
        )

    @action(detail=False, methods=["get"], 
            url_path="by-train/(?P<train_number>[^/]+)")
    def schedule_by_train(self, request, train_number=None):
        """
        Returns all active schedules for a given train number.
        Raises exception if the train is not found.
        """
        train = Train.objects.filter(train_number=train_number).first()
        if not train:
            logger.error(f"train not found with number {train_number}")
            raise NotFoundException(TrainMessage.TRAIN_NOT_FOUND)
        schedules = self.get_queryset().filter(train=train)
        serialzer = self.get_serializer(schedules, many=True)
        return Response(serialzer.data, status=status.HTTP_200_OK)
