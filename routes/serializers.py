import logging
from rest_framework import serializers
from .models import RouteEdge, RouteTemplate
from stations.models import Station
from exceptions.handlers import (StationNotFoundException, RouteAlreadyExistsException,
                RouteInvalidDistanceException, RouteUnidrectionalException,
                RouteFromAndToSameException, RouteInvalidInputException)
from utils.constants import RouteMessage

logger = logging.getLogger("routes")

class RouteEdgeSerializer(serializers.ModelSerializer):
    """
    Validates all the route related fields and ensures the reduced redundancy.
    """
    from_station = serializers.CharField()
    to_station = serializers.CharField()

    class Meta:
        model = RouteEdge
        fields = ['id', 'from_station', 'to_station', 'distance']

    def validate_distance(self, value):
        """
        Vlidates the distance is positive integer.
        """
        if value <= 0:
            raise RouteInvalidDistanceException()
        return value

    def validate(self, attrs):
        """
        validates the route existing or not.
        """
        from_code = attrs.get('from_station')
        to_code = attrs.get('to_station')
        is_bidirectional = attrs.get('is_bidirectional', True)
        if from_code == to_code:
            raise RouteFromAndToSameException()
        # Validate station codes
        try:
            from_station = Station.objects.get(code=from_code)
            to_station = Station.objects.get(code=to_code)
        except Station.DoesNotExist:
            raise StationNotFoundException(
                f"Station with code '{from_code}' not found - "
                f"Station with code '{to_code}' not found."
                )

        if is_bidirectional:
            if RouteEdge.objects.filter(
                from_station=from_station, to_station=to_station, is_bidirectional=True
            ).exists() or RouteEdge.objects.filter(
                from_station=to_station, to_station=from_station, is_bidirectional=True
            ).exists():
                raise RouteAlreadyExistsException()
        else:
            if RouteEdge.objects.filter(
                from_station=from_station, to_station=to_station, is_bidirectional=False
            ).exists():
                raise RouteUnidrectionalException()
        attrs['from_station'] = from_station
        attrs['to_station'] = to_station
        return attrs

    def to_representation(self, instance):
        rep = super().to_representation(instance)
        rep['from_station'] = instance.from_station.code
        rep['to_station'] = instance.to_station.code
        return rep
    
class RouteTemplateSerializer(serializers.ModelSerializer):
    from_station = serializers.CharField()
    to_station = serializers.CharField()

    class Meta:
        model = RouteTemplate
        fields = ['id', 'name', 'from_station', 'to_station', 'category', 'stops']

    def validate(self, request):
        from_code = request.get('from_station')
        to_code = request.get('to_station')
        category = request.get('category')
        stops = request.get('stops', [])

        if from_code == to_code:
            logger.error("from and to stations must be different.")
            raise RouteFromAndToSameException()
        
        try:
            from_station = Station.objects.get(code=from_code)
        except Station.DoesNotExist:
            logger.error(f"Station with with {from_code} not found.")
            raise StationNotFoundException(f"station not found.")
        
        try:
            to_station = Station.objects.get(code=to_code)
        except Station.DoesNotExist:
            logger.error(f"Station with code {to_code} not found.")
            raise StationNotFoundException()
        
        if category.lower() not in ['local', 'fast']:
            logger.error("Categories are only local and fast.")
            raise RouteInvalidInputException("Category must be 'local' or 'fast'.")
        
        if RouteTemplate.objects.filter(from_station=from_station,
                                        to_station=to_station,
                                        category=category
                                        ).exists():
            logger.error(f"A route template for this station and category exists.")
            raise RouteAlreadyExistsException()
        
        if category.lower() == 'fast':
            if not stops or not isinstance(stops, list) or len(stops) < 2:
                logger.error("For fast trains, 'stops' must be a list of at" + 
                             " least two station codes (including from and to).")
                raise RouteInvalidInputException()
        
        request['from_station'] = from_station
        request['to_station'] = to_station
        return request
    
    def to_representation(self, instance):
        rep = super().to_representation(instance)
        rep['from_station'] = instance.from_station.code
        rep['to_station'] = instance.to_station.code
        return rep