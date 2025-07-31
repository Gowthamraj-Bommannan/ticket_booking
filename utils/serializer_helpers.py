from rest_framework import serializers
from utils.constants import UserMessage
from utils.validators import UserFieldValidators


class RegistrationFieldMixin:
    """
    Mixin providing common field definitions for registration serializers.
    
    This mixin defines the standard fields used in both user and staff registration
    serializers to eliminate code duplication.
    """
    
    email = serializers.EmailField(validators=[])
    username = serializers.CharField(validators=[])
    mobile_number = serializers.CharField(validators=[])
    password = serializers.CharField(write_only=True)


class RegistrationValidationMixin:
    """
    Mixin providing common validation methods for registration serializers.
    
    This mixin contains validation methods that are shared between user and staff
    registration serializers, including field format validation and uniqueness checks.
    """
    
    def validate_email(self, value, registration_type):
        """
        Validates email uniqueness for registration.
        
        Args:
            value: Email value to validate
            registration_type: Type of registration ("registration" or "staff_registration")
            
        Returns:
            str: Validated email value
            
        Raises:
            AlreadyExistsException: If email already exists for active users
        """
        return UserFieldValidators.validate_email_uniqueness(value, registration_type)
    
    def validate_mobile_number(self, value, registration_type):
        """
        Validates mobile number format and uniqueness for registration.
        
        Args:
            value: Mobile number value to validate
            registration_type: Type of registration ("registration" or "staff_registration")
            
        Returns:
            str: Validated mobile number value
            
        Raises:
            ValidationError: If mobile number format is invalid
            AlreadyExistsException: If mobile number already exists for active users
        """
        value = value.strip()
        
        # Format validation
        if len(value) != 10:
            raise serializers.ValidationError(UserMessage.MOBILE_NUMBER_INVALID)
        
        if not value.isdigit() or not value.isascii():
            raise serializers.ValidationError(UserMessage.MOBILE_NUMBER_INVALID)
        
        return UserFieldValidators.validate_mobile_number_uniqueness(value, registration_type)
    
    def validate_username(self, value, registration_type):
        """
        Validates username format and uniqueness for registration.
        
        Args:
            value: Username value to validate
            registration_type: Type of registration ("registration" or "staff_registration")
            
        Returns:
            str: Validated username value
            
        Raises:
            ValidationError: If username is too short
            AlreadyExistsException: If username already exists
        """
        # Format validation
        if len(value) < 5:
            raise serializers.ValidationError(UserMessage.USERNAME_TOO_SHORT)
        
        return UserFieldValidators.validate_username_uniqueness(value, registration_type)


def get_registration_meta_fields():
    """
    Returns the standard Meta fields for registration serializers.
    
    Returns:
        list: List of field names for registration serializers
    """
    return [
        "username",
        "email", 
        "mobile_number",
        "password",
        "first_name",
        "last_name",
    ] 