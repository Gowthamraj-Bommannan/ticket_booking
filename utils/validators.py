from django.contrib.auth import get_user_model
from exceptions.handlers import AlreadyExistsException
from utils.constants import AlreadyExistsMessage
from exceptions.handlers import InvalidOTPException
import logging

User = get_user_model()
logger = logging.getLogger("accounts")

class UserFieldValidators:
    """
    Reusable validation mixins for user-related fields.
    Eliminates code duplication in serializers.
    """
    
    @staticmethod
    def validate_email_uniqueness(value, context="registration", exclude_user=None):
        """
        Validates email uniqueness for user registration and updates.
        Only checks against active users, allowing registration with inactive
        user credentials.
        """
        queryset = User.objects
        if exclude_user:
            queryset = queryset.exclude(pk=exclude_user.pk)
            
        if queryset.filter(email=value, is_active=True).exists():
            logger.error(f"{context.title()} failed - Email already exists: {value}")
            raise AlreadyExistsException(AlreadyExistsMessage.EMAIL_ALREADY_EXISTS)
        
        return value
    
    @staticmethod
    def validate_mobile_number_uniqueness(value, context="registration", exclude_user=None):
        """
        Validates mobile number uniqueness for user registration and updates.
        Only checks against active users, allowing registration with inactive
        user credentials.
            
        Returns:
            str: The validated mobile number
            
        Raises:
            AlreadyExistsException: If mobile number already exists
        """
        queryset = User.objects
        if exclude_user:
            queryset = queryset.exclude(pk=exclude_user.pk)
            
        if queryset.filter(mobile_number=value, is_active=True).exists():
            logger.error(f"{context.title()} failed - Mobile number already exists: {value}")
            raise AlreadyExistsException(
                AlreadyExistsMessage.MOBILE_ALREADY_EXISTS
                )
        
        return value
    
    @staticmethod
    def validate_username_uniqueness(value, context="registration", exclude_user=None):
        """
        Validates username uniqueness for user registration and updates.
        Username must be unique across ALL users (active and inactive).
            
        Returns:
            str: The validated username
            
        Raises:
            AlreadyExistsException: If username already exists
        """
        queryset = User.objects
        if exclude_user:
            queryset = queryset.exclude(pk=exclude_user.pk)
            
        # Username must be unique across ALL users (active and inactive)
        if queryset.filter(username=value).exists():
            logger.error(f"{context.title()} failed - Username already exists: {value}")
            raise AlreadyExistsException(AlreadyExistsMessage.USERNAME_ALREADY_EXISTS)
        
        return value


class OTPValidator:
    """
    Reusable OTP validation logic.
    """
    
    @staticmethod
    def validate_otp(otp, expected_otp="123456", context="registration"):
        """
        Validates OTP for registration processes.
            
        Returns:
            bool: True if OTP is valid
            
        Raises:
            InvalidOTPException: If OTP is invalid
        """
        
        if otp != expected_otp:
            logger.error(f"Invalid OTP provided for {context} - OTP: {otp}")
            raise InvalidOTPException()
        return True 