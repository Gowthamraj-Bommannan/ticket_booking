import logging
logger = logging.getLogger("trains")
from rest_framework import serializers
from .models import Train, TrainClass
from routes.serializers import TrainRouteStopSerializer
from exceptions.handlers import TrainAlreadyExistsException

class TrainClassSerializer(serializers.ModelSerializer):
    """
    Serializes train class data for API representation and validation.
    """
    class Meta:
        model = TrainClass
        fields = ['id', 'class_type', 'seat_capacity']

    def to_representation(self, instance):
        logger.debug(f"Serializing train class: {instance.class_type} (Capacity: {instance.seat_capacity})")
        return super().to_representation(instance)

    def validate_seat_capacity(self, value):
        """
        Validates that seat capacity is a positive integer.
        """
        logger.debug(f"Validating seat capacity: {value}")
        if value <= 0:
            logger.error(f"Invalid seat capacity: {value}")
            raise serializers.ValidationError("Seat capacity must be a positive integer.")
        return value

class TrainSerializer(serializers.ModelSerializer):
    """
    Serializes train data, including classes and route, for API responses.
    """
    classes = TrainClassSerializer(many=True, read_only=True)
    route = serializers.SerializerMethodField()
    
    class Meta:
        model = Train
        fields = ['id', 'train_number', 'name', 'train_type', 'running_days', 'classes', 'route', 'is_active', 'created_at', 'updated_at']
        read_only_fields = ['created_at', 'updated_at']

    def to_representation(self, instance):
        logger.debug(f"Serializing train: {instance.name} ({instance.train_number})")
        return super().to_representation(instance)

    def get_route(self, obj):
        """
        Returns the serialized route stops for the train.
        """
        logger.debug(f"Getting route for train: {obj.name} ({obj.train_number})")
        stops = obj.route_stops.order_by('sequence')
        return TrainRouteStopSerializer(stops, many=True).data

class TrainCreateUpdateSerializer(serializers.ModelSerializer):
    """
    Serializes and validates train creation and update requests.
    """
    classes = TrainClassSerializer(many=True)
    train_number = serializers.CharField(required=False, read_only=True)
    
    class Meta:
        model = Train
        fields = ['train_number', 'name', 'train_type', 'running_days', 'classes']

    def validate_name(self, value):
        """
        Validates that the train name is unique among active trains.
        """
        logger.debug(f"Validating train name: {value}")
        # Check for case-insensitive uniqueness among active trains
        # During update, exclude the current instance
        queryset = Train.objects.filter(name__iexact=value)
        if self.instance:
            queryset = queryset.exclude(pk=self.instance.pk)
        
        if queryset.exists():
            logger.error(f"Train name already exists: {value}")
            raise TrainAlreadyExistsException()
        return value

    def validate_running_days(self, value):
        """
        Validates that running days are provided and valid.
        """
        logger.debug(f"Validating running days: {value}")
        if not value:
            logger.error("No running days specified.")
            raise serializers.ValidationError("At least one running day must be specified.")
        
        # Validate that all days are valid choices
        valid_days = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
        for day in value:
            if day not in valid_days:
                logger.error(f"Invalid running day: {day}")
                raise serializers.ValidationError(f"Invalid running day: {day}. Must be one of {valid_days}")
        
        return value

    def validate_classes(self, value):
        """
        Validates that classes are provided, unique, and valid.
        """
        logger.debug(f"Validating train classes: {value}")
        if not value:
            logger.error("No classes specified.")
            raise serializers.ValidationError("At least one class must be specified.")
        
        # Check for duplicate class types
        class_types = [item['class_type'] for item in value]
        if len(class_types) != len(set(class_types)):
            logger.error("Duplicate class types found.")
            raise serializers.ValidationError("Duplicate class types are not allowed.")
        
        # Validate class types are valid
        valid_class_types = ['General', 'Sleeper', 'AC']
        for class_data in value:
            if class_data['class_type'] not in valid_class_types:
                logger.error(f"Invalid class type: {class_data['class_type']}")
                raise serializers.ValidationError(f"Invalid class type: {class_data['class_type']}. Must be one of {valid_class_types}")
        
        return value

    def validate(self, data):
        """
        Performs additional cross-field validation for train creation/update.
        """
        logger.debug(f"Cross-field validation for train: {data}")
        # Additional cross-field validation if needed
        return data 