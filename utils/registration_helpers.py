from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.exceptions import ValidationError as DRFValidationError
from django.contrib.auth import get_user_model
from accounts.serializers import UserSerializer
from .validators import OTPValidator
from accounts.models import StaffRequest, UserOTPVerification, Role
from utils.constants import UserMessage, GeneralMessage
from exceptions.handlers import (
            AlreadyExistsException,
            PermissionDeniedException,
            InvalidInputException,
            TimeoutException,
            NotFoundException,
        )
from django.utils import timezone
from datetime import timedelta
import random
import string
import logging

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


class OTPHelper:
    """
    Centralized OTP management utilities to eliminate code duplication.
    """
    
    @staticmethod
    def generate_and_send_otp(email, validated_data, role):
        """
        Generate OTP and send it to the user.
        
        Args:
            email (str): User's email address
            validated_data (dict): Validated registration data
            role (Role): User's role object
            
        Returns:
            Response: OTP sent response
        """
        # Generate 6-digit OTP
        otp_code = ''.join(random.choices(string.digits, k=6))
        
        # Set expiry time (5 minutes from now)
        expiry_time = timezone.now() + timedelta(minutes=5)
        
        # Create or update OTP record
        otp_record, created = UserOTPVerification.objects.get_or_create(
            email=email,
            defaults={
                'otp_code': otp_code,
                'expiry_time': expiry_time,
                'attempt_count': 0,
                'is_verified': False
            }
        )
        
        if not created:
            # Update existing record
            otp_record.otp_code = otp_code
            otp_record.expiry_time = expiry_time
            otp_record.attempt_count = 0
            otp_record.is_verified = False
            otp_record.save()
        
        # Send OTP (mock implementation)
        logger.info(f"OTP {otp_code} sent to {email}")
        
        return Response({
            "message": UserMessage.OTP_SENT_REGISTRATION,
            "otp": otp_code  # Remove this in production
        }, status=202)
    
    @staticmethod
    def validate_otp_and_get_record(email, otp_code):
        """
        Validate OTP and return the OTP record.
        
        Args:
            email (str): User's email address
            otp_code (str): OTP code to validate
            
        Returns:
            UserOTPVerification: Valid OTP record
            
        Raises:
            InvalidInputException: If OTP not found or invalid
            TimeoutException: If OTP is expired
        """
        try:
            otp_record = UserOTPVerification.objects.get(email=email)
        except UserOTPVerification.DoesNotExist:
            raise InvalidInputException("No OTP found for this email. Please register again.")
        
        # Check if OTP is expired
        if otp_record.is_expired:
            otp_record.delete()
            raise TimeoutException(UserMessage.OTP_EXPIRED)
        
        # Check if OTP is correct
        if otp_record.otp_code != otp_code:
            otp_record.attempt_count += 1
            
            # If 3 or more failed attempts, delete the record
            if otp_record.attempt_count >= 3:
                otp_record.delete()
                raise InvalidInputException("Too many failed attempts. Please register again.")
            
            otp_record.save()
            raise InvalidInputException(UserMessage.INVALID_OTP)
        
        return otp_record
    
    @staticmethod
    def cleanup_otp_record(otp_record):
        """
        Mark OTP as verified and delete the record.
        
        Args:
            otp_record (UserOTPVerification): OTP record to cleanup
        """
        otp_record.is_verified = True
        otp_record.save()
        otp_record.delete()


class UserCreationHelper:
    """
    Centralized user creation utilities to eliminate code duplication.
    """
    
    @staticmethod
    def create_user_with_role(validated_data, role, is_active=True):
        """
        Create a user with the specified role and active status.
        
        Args:
            validated_data (dict): Validated user data
            role (Role): User's role object
            is_active (bool): Whether user should be active
            
        Returns:
            User: Created user object
            
        Raises:
            InvalidInputException: If user creation fails
        """
        try:
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
            return user
        except Exception as e:
            logger.error(f"Error creating user: {str(e)}")
            raise InvalidInputException("Failed to create user account. Please try again.")
    
    @staticmethod
    def generate_user_tokens(user):
        """
        Generate JWT tokens for a user.
        
        Args:
            user (User): User object
            
        Returns:
            dict: Token data
        """
        refresh = RefreshToken.for_user(user)
        return {
            "refresh": str(refresh),
            "access": str(refresh.access_token),
        }
    
    @staticmethod
    def create_user_registration_response(user, include_tokens=True):
        """
        Create standardized user registration response.
        
        Args:
            user (User): Created user object
            include_tokens (bool): Whether to include JWT tokens
            
        Returns:
            Response: Registration success response
        """
        response_data = {
            "message": "Registration successful!",
            "user": UserSerializer(user).data,
        }
        
        if include_tokens:
            response_data["tokens"] = UserCreationHelper.generate_user_tokens(user)
        
        return Response(response_data, status=201)
    
    @staticmethod
    def create_staff_registration_response(user):
        """
        Create standardized staff registration response.
        
        Args:
            user (User): Created staff user object
            
        Returns:
            Response: Staff registration success response
        """
        return Response({
            "message": UserMessage.STAFF_REGISTRATION_WAITING,
            "user_id": user.id
        }, status=201)


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


class StaffRequestHelper:
    """
    Centralized staff request management utilities.
    """
    
    @staticmethod
    def get_staff_request_or_404(pk):
        """
        Get staff request by PK or raise 404.
        
        Args:
            pk (int): Staff request primary key
            
        Returns:
            StaffRequest: Staff request object
            
        Raises:
            NotFoundException: If staff request not found
        """
        try:
            return StaffRequest.objects.get(pk=pk)
        except StaffRequest.DoesNotExist:
            raise NotFoundException(UserMessage.STAFF_REQUEST_NOT_FOUND)
    
    @staticmethod
    def validate_staff_request_status(staff_request):
        """
        Validate that staff request is pending.
        
        Args:
            staff_request (StaffRequest): Staff request object
            
        Raises:
            InvalidInputException: If request already processed
        """
        if staff_request.status != "pending":
            raise InvalidInputException("Staff request has already been processed.")
    
    @staticmethod
    def approve_staff_request(staff_request, admin_user):
        """
        Approve a staff request and activate the user.
        
        Args:
            staff_request (StaffRequest): Staff request to approve
            admin_user (User): Admin user performing the approval
        """
        staff_request.status = "approved"
        staff_request.processed_at = timezone.now()
        staff_request.processed_by = admin_user
        staff_request.save()

        # Activate the user
        user = staff_request.user
        user.is_active = True
        user.save()
    
    @staticmethod
    def reject_staff_request(staff_request, admin_user):
        """
        Reject a staff request and deactivate the user.
        
        Args:
            staff_request (StaffRequest): Staff request to reject
            admin_user (User): Admin user performing the rejection
        """
        staff_request.status = "rejected"
        staff_request.processed_at = timezone.now()
        staff_request.processed_by = admin_user
        staff_request.save()

        # Deactivate the user
        user = staff_request.user
        user.is_active = False
        user.save()