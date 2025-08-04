from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.exceptions import ValidationError as DRFValidationError
from django.contrib.auth import get_user_model
from accounts.serializers import UserSerializer
from .validators import OTPValidator
from accounts.models import StaffRequest
from utils.constants import UserMessage, GeneralMessage
import logging
from exceptions.handlers import (
            AlreadyExistsException,
            PermissionDeniedException,
            InvalidInputException,
        )

User = get_user_model()
logger = logging.getLogger("accounts")


def send_otp(mobile_number, email):
    """
    Sends OTP to the provided mobile number and email address.

    This is a mock implementation that simulates OTP sending functionality.
    In production, this should integrate with actual SMS/email gateways.

    Args:
        mobile_number (str): The mobile number to send OTP to
        email (str): The email address to send OTP to

    Returns:
        str: The OTP code (always returns '123456' for demo purposes)
    """
    logger.debug(f"OTP sent to mobile: {mobile_number} and email: {email}")
    return "123456"  # Always returns 123456 for demo


class RegistrationFlowHelper:
    """
    Reusable registration flow logic to eliminate code duplication.
    """
    
    @staticmethod
    def handle_registration_request(request, serializer, context="registration"):
        """
        Handles the common registration request logic for both user and staff registration.
        
        Args:
            request: HTTP request object
            serializer: Validated serializer instance
            context (str): Context for logging and messages
            
        Returns:
            Response: Appropriate response based on OTP presence
        """

        if not request.data.get("otp"):
            return RegistrationFlowHelper._send_otp_response(
                serializer.validated_data["mobile_number"],
                serializer.validated_data["email"],
                context
                )

        # Validate OTP
        OTPValidator.validate_otp(request.data.get("otp"), context=context)
        
        return RegistrationFlowHelper._complete_registration(serializer, context)
    
    @staticmethod
    def _send_otp_response(mobile_number, email, context="registration"):
        """Send OTP and return response"""
        send_otp(mobile_number, email)
        
        if context == "staff_registration":
            message = UserMessage.OTP_SENT_STAFF_REGISTRATION
        else:
            message = UserMessage.OTP_SENT_REGISTRATION
            
        logger.info(f"OTP sent for {context} - Email: {email}, Mobile: {mobile_number}")
        return Response({"detail": message, "otp": "123456"}, status=202)
    
    @staticmethod
    def _complete_registration(serializer, context="registration"):
        """Complete the registration process"""
        
        validated_data = serializer.validated_data
        
        # Determine role based on context
        role = "station_master" if context == "staff_registration" else "user"
        is_active = False if context == "staff_registration" else True
        
        # Create user
        user = User.objects.create_user(
            username=validated_data["username"],
            email=validated_data["email"],
            mobile_number=validated_data["mobile_number"],
            password=validated_data["password"],
            first_name=validated_data.get("first_name", ""),
            last_name=validated_data.get("last_name", ""),
            role=role,
            is_active=is_active,
        )
        
        logger.info(f"{context.title()} user created successfully - Username: {user.username}, Email: {user.email}")
        
        # Handle staff request creation if needed
        if context == "staff_registration":
            StaffRequest.objects.get_or_create(user=user)
            logger.info(f"Staff user {user.username} (ID: {user.id}) registered successfully, waiting for approval")
            return Response(
                {
                    "detail": UserMessage.STAFF_REGISTRATION_WAITING,
                    "user": UserSerializer(user).data,
                },
                status=201,
            )
        
        # Generate tokens for regular registration
        refresh = RefreshToken.for_user(user)
        data = {
            "refresh": str(refresh),
            "access": str(refresh.access_token),
            "user": UserSerializer(user).data,
        }
        logger.info(f"User {user.username} (ID: {user.id}) registered successfully")
        return Response(data, status=201)
    
    @staticmethod
    def handle_registration_error(e, serializer, context="registration"):
        """
        Handles registration errors with consistent logging.
        
        Args:
            e: The exception that occurred
            serializer: The serializer instance
            context (str): Context for logging
            
        Raises:
            The original exception or InvalidInput
        """       
        if isinstance(e, (AlreadyExistsException, PermissionDeniedException)):
            logger.error(f"{context.title()} failed - {type(e).__name__}: {str(e)}")
            raise
        if isinstance(e, InvalidInputException):
            logger.error(f"{context.title()} failed - {type(e).__name__}: {str(e)}")
            raise
        if isinstance(e, DRFValidationError):
            logger.error(f"{context.title()} validation failed: {str(e)}")
            raise  # Re-raise the original ValidationError to preserve field-specific errors
        
        # Handle other validation errors
        logger.error(f"Unexpected error during {context}: {str(e)}", exc_info=True)
        raise Exception(GeneralMessage.SOMETHING_WENT_WRONG)