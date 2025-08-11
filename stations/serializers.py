import logging
from rest_framework import serializers
from .models import Station

logger = logging.getLogger("stations")

class StationSerializer(serializers.ModelSerializer):
    """
    Serializes station data for API representation and validation.
    """

    station_master_username = serializers.CharField(
        source="station_master.username", read_only=True
    )

    class Meta:
        model = Station
        fields = ["id", "name", "code", "city", "state", "station_master_username"]


class AssignStationMasterSerializer(serializers.Serializer):
    """
    Serializes the user_id for assigning a station master.
    """

    user_id = serializers.IntegerField()

    def validate_user_id(self, value):
        logger.debug(f"Validating user_id for station master assignment: {value}")
        return value
