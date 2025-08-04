import logging
from rest_framework import serializers
from .models import Train, TrainSchedule
from utils.validators import TrainValidators

logger = logging.getLogger("trains")


class TrainSerializer(serializers.ModelSerializer):
    """
    Serializes train data, including classes for API responses.
    """

    class Meta:
        model = Train
        fields = ["id", "train_number", "name", "train_type"]
        read_only_fields = ["id", "train_number"]


class TrainCreateUpdateSerializer(serializers.ModelSerializer):
    """
    Serializes and validates train creation and update requests.
    """

    train_number = serializers.CharField(required=False, read_only=True)

    class Meta:
        model = Train
        fields = ["train_number", "name", "train_type"]

    def validate_train_number(self, value):
        """
        Validates that the train number is unique among all trains if provided.
        """
        exclude_pk = self.instance.pk if self.instance else None
        return TrainValidators.validate_train_number_uniqueness(value, exclude_pk)

    def validate(self, data):
        """
        Performs additional cross-field validation for train creation/update.
        """
        return data


class TrainScheduleSerializer(serializers.ModelSerializer):
    """
    Serializes train schedule data for API representation and validation.
    """

    class Meta:
        model = TrainSchedule
        fields = [
            "id",
            "train",
            "route_template",
            "days_of_week",
            "start_time",
            "direction",
            "is_active",
            "stops_with_time",
        ]
        read_only_fields = ["id", "stops_with_time"]

    def validate(self, data):
        """
        Validates the train schedule data.
        Raises error if invalid.
        """
        train = data.get("train")
        direction = data.get("direction")
        start_time = data.get("start_time")
        
        # Only check if all required fields are present
        if train and direction and start_time:
            exclude_pk = self.instance.pk if self.instance else None
            TrainValidators.validate_schedule_uniqueness(train, start_time, direction, exclude_pk)
        
        return data
