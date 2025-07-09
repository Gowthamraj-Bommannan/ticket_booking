import logging
logger = logging.getLogger("stations")
from rest_framework import serializers
from .models import Station
from exceptions.handlers import StationAlreadyExistsException

class StationSerializer(serializers.ModelSerializer):
    """
    Serializes station data for API representation and validation.
    """
    station_master_username = serializers.CharField(source='station_master.username', read_only=True)
    def to_representation(self, instance):
        logger.debug(f"Serializing station: {instance.name} ({instance.code})")
        return super().to_representation(instance)

    def validate(self, data):
        logger.debug(f"Validating station data: {data}")
        return super().validate(data)

class AssignStationMasterSerializer(serializers.Serializer):
    """
    Serializes the user_id for assigning a station master.
    """
    user_id = serializers.IntegerField()
    def validate_user_id(self, value):
        logger.debug(f"Validating user_id for station master assignment: {value}")
        return value 