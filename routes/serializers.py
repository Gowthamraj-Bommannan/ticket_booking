import logging
from rest_framework import serializers
from .models import RouteEdge, RouteTemplate
from exceptions.handlers import (
    AlreadyExistsException,
    InvalidInputException,
)
from utils.constants import RouteMessage
from utils.validators import RouteValidators
from utils.serializer_helpers import StationCodeRepresentationMixin

logger = logging.getLogger("routes")


class RouteEdgeSerializer(StationCodeRepresentationMixin, serializers.ModelSerializer):
    """
    Serializes route edge data for API usage.
    Handles validation and representation.
    """

    from_station = serializers.CharField()
    to_station = serializers.CharField()

    class Meta:
        model = RouteEdge
        fields = ["id", "from_station", "to_station", "distance"]

    def validate_distance(self, value):
        """
        Validates the distance is positive integer.
        Raises error if invalid.
        """
        return RouteValidators.validate_distance(value)

    def validate(self, attrs):
        """
        Validates the route existing or not.
        """
        from_code = attrs.get("from_station")
        to_code = attrs.get("to_station")
        is_bidirectional = attrs.get("is_bidirectional", True)
        
        # Use centralized validation - single query for both stations
        from_station, to_station = RouteValidators.validate_station_pair(from_code, to_code)
        
        # Check if edge already exists
        RouteValidators.validate_edge_exists(from_station, to_station, is_bidirectional)
        
        attrs["from_station"] = from_station
        attrs["to_station"] = to_station
        return attrs


class RouteTemplateSerializer(StationCodeRepresentationMixin, serializers.ModelSerializer):
    """
    Serializes route template data for API usage.
    Handles validation and representation.
    """

    from_station = serializers.CharField()
    to_station = serializers.CharField()

    class Meta:
        model = RouteTemplate
        fields = ["id", "name", "from_station", "to_station", "category", "stops"]

    def validate(self, request):
        """
        Validates the route template data.
        Raises error if invalid.
        """
        from_code = request.get("from_station")
        to_code = request.get("to_station")
        category = request.get("category")
        stops = request.get("stops", [])
        
        # Use centralized validation - single query for both stations
        from_station, to_station = RouteValidators.validate_station_pair(from_code, to_code)
        
        # Validate category
        category = self._validate_category(category)
        
        # Check if template already exists
        self._validate_template_exists(from_station, to_station, category)
        
        # Validate stops for fast trains
        self._validate_fast_train_stops(stops, category)
        
        request["from_station"] = from_station
        request["to_station"] = to_station
        return request

    def _validate_category(self, category):
        """
        Validates route template category.
        
        Args:
            category (str): Category to validate
            
        Returns:
            str: Validated category
            
        Raises:
            InvalidInputException: If category is invalid
        """
        valid_categories = ["local", "fast"]
        if category.lower() not in valid_categories:
            logger.error("Categories are only local and fast.")
            raise InvalidInputException(RouteMessage.ROUTE_EDGE_CATEGORY_INVALID)
        
        return category.lower()
    
    def _validate_template_exists(self, from_station, to_station, category):
        """
        Validates if a route template already exists.
        
        Args:
            from_station (Station): From station object
            to_station (Station): To station object
            category (str): Template category
            
        Raises:
            AlreadyExistsException: If template already exists
        """
        exists = RouteTemplate.objects.filter(
            from_station=from_station,
            to_station=to_station,
            category=category
        ).exists()
        
        if exists:
            logger.error("Route template for this station and category exists.")
            raise AlreadyExistsException(RouteMessage.ROUTE_EDGE_ALREADY_EXISTS)
    
    def _validate_fast_train_stops(self, stops, category):
        """
        Validates stops for fast train templates.
        
        Args:
            stops (list): List of stops
            category (str): Template category
            
        Raises:
            InvalidInputException: If stops are invalid for fast trains
        """
        if category.lower() == "fast":
            if not stops or not isinstance(stops, list) or len(stops) < 2:
                logger.error(
                    "For fast trains, 'stops' must be a list of at"
                    + " least two station codes (including from and to)."
                )
                raise InvalidInputException(RouteMessage.ROUTE_EDGE_INVALID_INPUT)
