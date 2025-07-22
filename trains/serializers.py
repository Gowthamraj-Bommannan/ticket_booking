import logging
from rest_framework import serializers
from .models import Train, TrainClass, TrainSchedule
from utils.constants import TrainMessage
from exceptions.handlers import ScheduleAlreadyExists
from utils.constants import TrainMessage
from exceptions.handlers import (TrainAlreadyExistsException,
                                 ScheduleAlreadyExists)

logger = logging.getLogger("trains")

class TrainClassSerializer(serializers.ModelSerializer):
    """
    Serializes train class data for API representation and validation.
    """
    class Meta:
        model = TrainClass
        fields = ['id', 'class_type']

class TrainSerializer(serializers.ModelSerializer):
    """
    Serializes train data, including classes for API responses.
    """
    classes = TrainClassSerializer(many=True, read_only=True)
    
    class Meta:
        model = Train
        fields = ['id', 'train_number', 'name', 'train_type', 'classes']
        read_only_fields = ['id', 'train_number']

class TrainCreateUpdateSerializer(serializers.ModelSerializer):
    """
    Serializes and validates train creation and update requests.
    """
    classes = TrainClassSerializer(many=True, required=True)
    train_number = serializers.CharField(required=False, read_only=True)
    
    class Meta:
        model = Train
        fields = ['train_number', 'name', 'train_type', 'classes']

    def validate_train_number(self, value):
        """
        Validates that the train number is unique among all trains if provided.
        """
        queryset = Train.all_objects.filter(train_number=value)
        if self.instance:
            queryset = queryset.exclude(pk=self.instance.pk)
        if queryset.exists():
            logger.error(f"Train number already exists: {value}")
            raise TrainAlreadyExistsException()
        return value

    def validate_classes(self, value):
        """
        Validates that classes are provided, unique, and valid.
        """
        if not value:
            logger.error("No classes specified.")
            raise serializers.ValidationError(TrainMessage.TRAIN_CLASSES_MUST_DEFINED)
        
        class_types = [item['class_type'] for item in value]
        if len(class_types) != len(set(class_types)):
            logger.error("Duplicate class types found.")
            raise serializers.ValidationError(TrainMessage.TRAIN_DUPLICATE_CLASS)
        
        valid_class_types = [choice[0] for choice in TrainClass.CLASS_TYPE_CHOICES]
        for class_data in value:
            if class_data['class_type'] not in valid_class_types:
                logger.error(f"Invalid class type: {class_data['class_type']}")
                raise serializers.ValidationError(TrainMessage.TRAIN_CLASS_INVALID)
        
        return value

    def validate(self, data):
        """
        Performs additional cross-field validation for train creation/update.
        """
        return data 
    
class TrainScheduleSerializer(serializers.ModelSerializer):
    class Meta:
        model = TrainSchedule
        fields = [
            'id', 'train', 'route_template', 'days_of_week', 'start_time',
            'direction', 'is_active', 'stops_with_time'
        ]
        read_only_fields = ['id', 'stops_with_time']

    def validate(self, data):
        train = data.get('train')
        direction = data.get('direction')
        start_time = data.get('start_time')
        # Only check if all required fields are present
        if train and direction and start_time:
            qs = TrainSchedule.objects.filter(
                train=train,
                start_time=start_time,
                direction=direction,
                is_active=True
            )
            if self.instance:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise ScheduleAlreadyExists(TrainMessage.SCHEDULE_ALREADY_EXISTS)
        return data