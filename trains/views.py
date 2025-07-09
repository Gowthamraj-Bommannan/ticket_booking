import logging
logger = logging.getLogger("trains")
from django.shortcuts import render
from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.permissions import BasePermission, IsAuthenticated
from rest_framework.decorators import action
from django.shortcuts import get_object_or_404
from django.http import Http404
from .models import Train, TrainClass
from .serializers import TrainSerializer, TrainCreateUpdateSerializer
from exceptions.handlers import (
    TrainNotFoundException, TrainAlreadyInactiveException, 
    TrainAlreadyActiveException, TrainInactiveException
)

class IsAdminSuperUser(BasePermission):
    """
    Allows access only to admin users with is_superuser=True.
    """
    def has_permission(self, request, view):
        logger.info(f"Checking IsAdminSuperUser permission for user: {request.user.username}")
        permission_granted = bool(
            request.user and 
            request.user.is_authenticated and
            request.user.role == 'admin' and 
            request.user.is_superuser
        )
        logger.info(f"IsAdminSuperUser permission granted: {permission_granted}")
        return permission_granted

class IsAdminOrStationMaster(BasePermission):
    """
    Allows access to admin users or station masters.
    """
    def has_permission(self, request, view):
        logger.info(f"Checking IsAdminOrStationMaster permission for user: {request.user.username}")
        permission_granted = bool(
            request.user and 
            request.user.is_authenticated and
            request.user.role in ['admin', 'station_master']
        )
        logger.info(f"IsAdminOrStationMaster permission granted: {permission_granted}")
        return permission_granted

class TrainViewSet(viewsets.ModelViewSet):
    """
    Provides CRUD and soft delete endpoints for trains.
    """
    queryset = Train.objects.all()
    lookup_field = 'train_number'
    
    def get_serializer_class(self):
        """
        Returns the appropriate serializer class based on the action.
        """
        if self.action in ['create', 'update', 'partial_update']:
            return TrainCreateUpdateSerializer
        return TrainSerializer
    
    def get_permissions(self):
        """
        Returns the appropriate permissions based on the action.
        """
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            permission_classes = [IsAdminSuperUser]
        elif self.action in ['deactivate', 'activate']:
            permission_classes = [IsAdminOrStationMaster]
        else:
            permission_classes = [IsAuthenticated]
        return [permission() for permission in permission_classes]
    
    def get_queryset(self):
        """
        Returns the queryset of trains, filtered by train_type if provided.
        """
        qs = super().get_queryset()
        train_type = self.request.query_params.get('train_type')
        if train_type:
            qs = qs.filter(train_type=train_type)
        return qs
    
    def get_object(self):
        """
        Retrieves a train, raising custom exceptions for inactive or missing trains.
        """
        try:
            return super().get_object()
        except Http404:
            # Check if train exists but is inactive
            train_number = self.kwargs.get('train_number')
            if train_number:
                inactive_train = Train.all_objects.filter(train_number=train_number, is_active=False).first()
                if inactive_train:
                    raise TrainInactiveException()
            raise TrainNotFoundException()
    
    def create(self, request, *args, **kwargs):
        """
        Handles train creation with associated classes.
        """
        logger.info(f"Attempting to create train with data: {request.data}")
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        # Extract validated data
        validated_data = serializer.validated_data
        classes_data = validated_data.pop('classes')
        
        # Create train with business logic moved from serializer
        train = Train.objects.create(**validated_data)
        
        # Create train classes
        for class_data in classes_data:
            TrainClass.objects.create(train=train, **class_data)
        
        # Return response with created train data
        response_serializer = TrainSerializer(train)
        logger.info(f"Train created successfully: {train.train_number}")
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)
    
    def update(self, request, *args, **kwargs):
        """
        Handles train update, including class updates.
        """
        instance = self.get_object()
        logger.info(f"Attempting to update train with data: {request.data}")
        serializer = self.get_serializer(instance, data=request.data, partial=kwargs.get('partial', False))
        serializer.is_valid(raise_exception=True)
        
        # Extract validated data
        validated_data = serializer.validated_data
        classes_data = validated_data.pop('classes', [])
        
        # Update train fields (train_number cannot be updated)
        instance.name = validated_data.get('name', instance.name)
        instance.train_type = validated_data.get('train_type', instance.train_type)
        instance.running_days = validated_data.get('running_days', instance.running_days)
        instance.save()
        
        # Update classes - delete existing and create new ones
        instance.classes.all().delete()
        for class_data in classes_data:
            TrainClass.objects.create(train=instance, **class_data)
        
        # Return response with updated train data
        response_serializer = TrainSerializer(instance)
        logger.info(f"Train updated successfully: {instance.train_number}")
        return Response(response_serializer.data)
    
    @action(detail=True, methods=['delete'], url_path='remove')
    def deactivate(self, request, train_number=None):
        """
        Soft deletes a train by setting is_active=False.
        """
        logger.info(f"Attempting to deactivate train with train_number: {train_number}")
        train = get_object_or_404(Train.all_objects, train_number=train_number)
        
        if not train.is_active:
            raise TrainAlreadyInactiveException()
        
        train.is_active = False
        train.save()
        
        logger.info(f"Train deactivated successfully: {train.train_number}")
        return Response({
            'detail': f'Train {train.name} ({train.train_number}) has been deactivated.'
        }, status=status.HTTP_200_OK)
    
    @action(detail=True, methods=['post'], url_path='activate')
    def activate(self, request, train_number=None):
        """
        Reactivates a train by setting is_active=True.
        """
        logger.info(f"Attempting to activate train with train_number: {train_number}")
        train = get_object_or_404(Train.all_objects, train_number=train_number)
        
        if train.is_active:
            raise TrainAlreadyActiveException()
        
        train.is_active = True
        train.save()
        
        logger.info(f"Train activated successfully: {train.train_number}")
        return Response({
            'detail': f'Train {train.name} ({train.train_number}) has been activated.'
        }, status=status.HTTP_200_OK)

# Expose TrainViewSet for router registration
__all__ = ['TrainViewSet', 'IsAdminSuperUser', 'IsAdminOrStationMaster']
