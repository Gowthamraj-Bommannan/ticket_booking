import logging
logger = logging.getLogger("routes")
from rest_framework import serializers
from .models import TrainRouteStop, RouteTemplate, RouteTemplateStop
from trains.models import Train
from stations.models import Station
from datetime import datetime, timedelta
from exceptions.handlers import (
    RouteStopNotFoundException, RouteStopDuplicateSequenceException,
    RouteStopInvalidSequenceException, RouteStopDepartureMustGreaterException, 
    RouteStopStationInactiveException, RouteStopTrainInactiveException, 
    RouteStopInvalidInputException
)

class RouteTemplateStopSerializer(serializers.ModelSerializer):
    """
    Serializes route template stop data for API representation and validation.
    """
    station_code = serializers.CharField(source='station.code', read_only=True)
    station_name = serializers.CharField(source='station.name', read_only=True)
    
    class Meta:
        model = RouteTemplateStop
        fields = ['id', 'route_template', 'station', 'station_code', 'station_name', 'sequence', 
                 'distance_from_source', 'estimated_halt_minutes']

    def to_representation(self, instance):
        logger.debug(f"Serializing route template stop: {instance.id}")
        return super().to_representation(instance)

    def validate_sequence(self, value):
        logger.debug(f"Validating sequence for route template stop: {value}")
        """
        Validates that the stop sequence is unique within the template.
        """
        route_template = self.initial_data.get('route_template')
        if route_template:
            if RouteTemplateStop.objects.filter(route_template=route_template, sequence=value).exclude(pk=self.instance.pk if self.instance else None).exists():
                logger.error(f"Duplicate sequence {value} for route template {route_template}")
                raise serializers.ValidationError(f"Sequence {value} already exists for this template.")
        return value

    def validate(self, data):
        logger.debug(f"Validating route template stop data: {data}")
        """
        Validates that distance increases with sequence in the template.
        """
        # Validate distance increases with sequence
        if data.get('sequence', 0) > 1:
            route_template = data.get('route_template')
            if route_template:
                prev_stop = RouteTemplateStop.objects.filter(
                    route_template=route_template, 
                    sequence=data['sequence'] - 1
                ).exclude(pk=self.instance.pk if self.instance else None).first()
                if prev_stop and data.get('distance_from_source', 0) <= prev_stop.distance_from_source:
                    logger.error(f"Distance must increase with sequence for route_template {route_template}, sequence {data['sequence']}")
                    raise serializers.ValidationError({'distance_from_source': 'Distance must increase with sequence.'})
        return super().validate(data)

class RouteTemplateSerializer(serializers.ModelSerializer):
    """
    Serializes route template data, including stops, for API responses.
    """
    template_stops = RouteTemplateStopSerializer(many=True, read_only=True)
    source_station_code = serializers.CharField(source='source_station.code', read_only=True)
    source_station_name = serializers.CharField(source='source_station.name', read_only=True)
    destination_station_code = serializers.CharField(source='destination_station.code', read_only=True)
    destination_station_name = serializers.CharField(source='destination_station.name', read_only=True)
    
    class Meta:
        model = RouteTemplate
        fields = ['id', 'name', 'description', 'source_station', 'source_station_code', 
                 'source_station_name', 'destination_station', 'destination_station_code', 
                 'destination_station_name', 'total_distance', 'estimated_duration', 
                 'template_stops', 'created_at', 'updated_at']
        read_only_fields = ['created_at', 'updated_at']

    def to_representation(self, instance):
        logger.debug(f"Serializing route template: {instance.id}")
        return super().to_representation(instance)

class TrainRouteStopSerializer(serializers.ModelSerializer):
    """
    Serializes train route stop data for API representation.
    """
    train_number = serializers.CharField(source='train.train_number', read_only=True)
    train_name = serializers.CharField(source='train.name', read_only=True)
    station_code = serializers.CharField(source='station.code', read_only=True)
    station_name = serializers.CharField(source='station.name', read_only=True)
    
    class Meta:
        model = TrainRouteStop
        fields = ['id', 'train', 'train_number', 'train_name', 'station', 'station_code', 
                 'station_name', 'sequence', 'arrival_time', 'departure_time', 'halt_minutes', 
                 'distance_from_source', 'day_count', 'created_at', 'updated_at']
        read_only_fields = ['created_at', 'updated_at', 'halt_minutes']

    def to_representation(self, instance):
        logger.debug(f"Serializing train route stop: {instance.id}")
        return super().to_representation(instance)

class TrainRouteStopCreateSerializer(serializers.ModelSerializer):
    """
    Serializes and validates creation of a train route stop.
    """
    station_code = serializers.CharField(write_only=True)
    
    class Meta:
        model = TrainRouteStop
        fields = ['station_code', 'sequence', 'arrival_time', 'departure_time', 
                 'halt_minutes', 'distance_from_source', 'day_count']

    def validate_station_code(self, value):
        logger.debug(f"Validating station code for train route stop: {value}")
        """
        Validates that the station exists and is active.
        """
        if not Station.objects.filter(code=value).exists():
            logger.error(f"Station not found: {value}")
            raise RouteStopNotFoundException()
        station = Station.objects.get(code=value)
        if not station.is_active:
            logger.error(f"Station inactive: {value}")
            raise RouteStopStationInactiveException()
        return value

    def validate_sequence(self, value):
        logger.debug(f"Validating sequence for train route stop: {value}")
        """
        Validates that the stop sequence is unique for the train.
        """
        # Get train from context
        train = self.context.get('train')
        if train and TrainRouteStop.objects.filter(train=train, sequence=value).exists():
            logger.error(f"Duplicate sequence {value} for train {train.train_number}")
            raise RouteStopDuplicateSequenceException()
        return value

    def validate(self, data):
        logger.debug(f"Validating train route stop data: {data}")
        """
        Performs all business validation for creating a route stop.
        """
        train = self.context.get('train')
        if not train:
            logger.error("No train provided in context for train route stop creation.")
            raise RouteStopInvalidInputException()
        if not train.is_active:
            logger.error(f"Train {getattr(train, 'train_number', None)} is inactive.")
            raise RouteStopTrainInactiveException()
        
        # Validate distance increases with sequence
        if data.get('sequence', 0) > 1:
            prev_stop = TrainRouteStop.objects.filter(
                train=train, 
                sequence=data['sequence'] - 1
            ).first()
            if prev_stop and data.get('distance_from_source', 0) <= prev_stop.distance_from_source:
                logger.error(f"Distance must increase with sequence for train {train.train_number}, sequence {data['sequence']}")
                raise RouteStopInvalidSequenceException()
        
        # Validate arrival/departure times
        arrival_time = data.get('arrival_time')
        departure_time = data.get('departure_time')
        
        if arrival_time and departure_time:
            if arrival_time >= departure_time:
                logger.error(f"Arrival time {arrival_time} is not before departure time {departure_time} for train {getattr(train, 'train_number', None)}.")
                raise RouteStopDepartureMustGreaterException()
            
            # Auto-calculate halt minutes
            arrival_dt = datetime.combine(datetime.today(), arrival_time)
            departure_dt = datetime.combine(datetime.today(), departure_time)
            if departure_dt < arrival_dt:
                departure_dt += timedelta(days=1)
            data['halt_minutes'] = int((departure_dt - arrival_dt).total_seconds() / 60)
        
        # Validate timing with previous stop
        if data.get('sequence', 0) > 1:
            prev_stop = TrainRouteStop.objects.filter(
                train=train, 
                sequence=data['sequence'] - 1
            ).first()
            if prev_stop and prev_stop.departure_time and arrival_time:
                # Check if arrival is after previous departure
                prev_departure = datetime.combine(datetime.today(), prev_stop.departure_time)
                current_arrival = datetime.combine(datetime.today(), arrival_time)
                
                # Handle day change
                day_count = data.get('day_count', 1)
                if prev_stop.day_count < day_count:
                    current_arrival += timedelta(days=day_count - prev_stop.day_count)
                
                if current_arrival <= prev_departure:
                    logger.error(f"Current arrival {current_arrival} is not after previous departure {prev_departure} for train {train.train_number}, sequence {data['sequence']}")
                    raise RouteStopInvalidSequenceException()
        
        # Auto-calculate day_count if not provided
        if not data.get('day_count') and data.get('sequence', 0) > 1:
            prev_stop = TrainRouteStop.objects.filter(
                train=train, 
                sequence=data['sequence'] - 1
            ).first()
            if prev_stop and prev_stop.departure_time and arrival_time:
                prev_departure = datetime.combine(datetime.today(), prev_stop.departure_time)
                current_arrival = datetime.combine(datetime.today(), arrival_time)
                
                if current_arrival < prev_departure:
                    data['day_count'] = prev_stop.day_count + 1
                else:
                    data['day_count'] = prev_stop.day_count
            else:
                data['day_count'] = 1
        
        return super().validate(data)

class TrainRouteStopUpdateSerializer(serializers.ModelSerializer):
    """
    Serializes and validates updates to a train route stop.
    """

    class Meta:
        model = TrainRouteStop
        fields = ['sequence', 'arrival_time', 'departure_time', 'halt_minutes', 
                 'distance_from_source', 'day_count']

    def validate_sequence(self, value):
        logger.debug(f"Validating sequence for train route stop update: {value}")
        """
        Validates that the stop sequence is unique for the train.
        """
        instance = self.instance
        if instance and TrainRouteStop.objects.filter(
            train=instance.train, 
            sequence=value
        ).exclude(pk=instance.pk).exists():
            logger.error(f"Duplicate sequence {value} for train {instance.train.train_number}")
            raise RouteStopDuplicateSequenceException()
        return value

    def validate(self, data):
        logger.debug(f"Validating train route stop update data: {data}")
        """
        Performs all business validation for updating a route stop.
        """
        instance = self.instance
        if not instance:
            logger.error("No instance provided for train route stop update.")
            raise RouteStopInvalidInputException()
        
        # Validate distance increases with sequence
        sequence = data.get('sequence', instance.sequence)
        if sequence > 1:
            prev_stop = TrainRouteStop.objects.filter(
                train=instance.train, 
                sequence=sequence - 1
            ).exclude(pk=instance.pk).first()
            distance = data.get('distance_from_source', instance.distance_from_source)
            if prev_stop and distance <= prev_stop.distance_from_source:
                logger.error(f"Distance must increase with sequence for train {instance.train.train_number}, sequence {sequence}")
                raise RouteStopInvalidSequenceException()
        
        # Validate arrival/departure times
        arrival_time = data.get('arrival_time', instance.arrival_time)
        departure_time = data.get('departure_time', instance.departure_time)
        
        if arrival_time and departure_time:
            if arrival_time >= departure_time:
                logger.error(f"Arrival time {arrival_time} is not before departure time {departure_time} for train {getattr(instance.train, 'train_number', None)}.")
                raise RouteStopDepartureMustGreaterException()
            
            # Auto-calculate halt minutes
            arrival_dt = datetime.combine(datetime.today(), arrival_time)
            departure_dt = datetime.combine(datetime.today(), departure_time)
            if departure_dt < arrival_dt:
                departure_dt += timedelta(days=1)
            data['halt_minutes'] = int((departure_dt - arrival_dt).total_seconds() / 60)
        
        # Validate timing with previous stop
        if sequence > 1:
            prev_stop = TrainRouteStop.objects.filter(
                train=instance.train, 
                sequence=sequence - 1
            ).exclude(pk=instance.pk).first()
            if prev_stop and prev_stop.departure_time and arrival_time:
                # Check if arrival is after previous departure
                prev_departure = datetime.combine(datetime.today(), prev_stop.departure_time)
                current_arrival = datetime.combine(datetime.today(), arrival_time)
                
                # Handle day change
                day_count = data.get('day_count', instance.day_count)
                if prev_stop.day_count < day_count:
                    current_arrival += timedelta(days=day_count - prev_stop.day_count)
                
                if current_arrival <= prev_departure:
                    logger.error(f"Current arrival {current_arrival} is not after previous departure {prev_departure} for train {instance.train.train_number}, sequence {sequence}")
                    raise RouteStopInvalidSequenceException()
        
        return super().validate(data)

class TrainRouteSerializer(serializers.ModelSerializer):
    """
    Serializes a full train route with all stops for API responses.
    """
    route_stops = TrainRouteStopSerializer(many=True, read_only=True)
    
    class Meta:
        model = Train
        fields = ['train_number', 'name', 'train_type', 'route_stops']

    def to_representation(self, instance):
        logger.debug(f"Serializing train route: {instance.train_number}")
        return super().to_representation(instance)

class CreateTrainFromTemplateSerializer(serializers.Serializer):
    """
    Serializes data for creating a train route from a template.
    """
    train_number = serializers.CharField()
    start_time = serializers.TimeField(input_formats=['%H:%M:%S', '%H:%M'])

    def validate_train_number(self, value):
        logger.debug(f"Validating train number for route creation: {value}")
        """
        Validates that the train number exists.
        """
        if not Train.objects.filter(train_number=value).exists():
            logger.error(f"Train not found: {value}")
            raise serializers.ValidationError(f"Train with number '{value}' does not exist.")
        return value 