from rest_framework import serializers
from django.contrib.auth import authenticate
from .models import User, StaffRequest
from exceptions.handlers import InvalidCredentialsException
from utils.constants import UserMessage
from utils.validators import UserFieldValidators
from utils.serializer_helpers import (
    RegistrationFieldMixin,
    RegistrationValidationMixin,
    get_registration_meta_fields,
)
import logging

logger = logging.getLogger("accounts")


class RegisterSerializer(RegistrationFieldMixin, RegistrationValidationMixin, serializers.ModelSerializer):
    """
    Serializer for user registration validation.

    This serializer handles validation for user registration including:
    - Data validation for all registration fields
    - Duplicate email and mobile number checking
    - Field format and constraint validation

    Provides comprehensive validation for user registration data.
    """

    class Meta:
        model = User
        fields = get_registration_meta_fields()

    def validate_email(self, value):
        """
        Validates email uniqueness for user registration.
        """
        return super().validate_email(value, "registration")

    def validate_mobile_number(self, value):
        """
        Validates mobile number format and uniqueness for user registration.
        """
        return super().validate_mobile_number(value, "registration")
    
    def validate_username(self, value):
        """
        Validates username format and uniqueness for user registration.
        """
        return super().validate_username(value, "registration")


class StaffRegisterSerializer(RegistrationFieldMixin, RegistrationValidationMixin, serializers.ModelSerializer):
    """
    Serializer for staff registration validation.

    This serializer handles validation for staff registration including:
    - Data validation for all registration fields
    - Duplicate email and mobile number checking
    - Field format and constraint validation

    Provides comprehensive validation for staff registration data.
    """

    class Meta:
        model = User
        fields = get_registration_meta_fields()

    def validate_email(self, value):
        """
        Validates email uniqueness for staff registration.
        """
        return super().validate_email(value, "staff_registration")

    def validate_mobile_number(self, value):
        """
        Validates mobile number format and uniqueness for staff registration.
        """
        return super().validate_mobile_number(value, "staff_registration")
    
    def validate_username(self, value):
        """
        Validates username format and uniqueness for staff registration.
        """
        return super().validate_username(value, "staff_registration")


class UserSerializer(serializers.ModelSerializer):
    """
    Serializer for user profile data display and management.

    This serializer provides comprehensive user information including:
    - Basic profile fields (username, email, mobile_number, names)
    - System fields (role, timestamps, active status)
    - Read-only fields for system-managed data

    Used for profile display, user data in responses, and general user information.
    """

    class Meta:
        model = User
        fields = ["id", "username", "email", "first_name", "role"]
        read_only_fields = ["role", "created_at", "last_login", "is_active"]


class LoginSerializer(serializers.Serializer):
    """
    Serializer for user authentication and login validation.

    This serializer handles user login process including:
    - Username and password field validation
    - User authentication using Django's authenticate function
    - User account status verification (active/inactive)
    - Custom validation for authentication failures

    Provides comprehensive authentication validation and error handling.
    """

    username = serializers.CharField()
    password = serializers.CharField(write_only=True)

    def validate(self, data):
        """
        Validates user credentials and account status for login.

        Authenticates user using provided username and password, checks
        if user account is active, and returns user object for successful login.

        Raises:
            InvalidCredentialsException: If username/password combination is invalid
            ValidationError: If user account is inactive
        """
        user = authenticate(username=data["username"], password=data["password"])
        if not user:
            logger.error(
                f"Login failed - Invalid credentials for username: {data['username']}"
            )
            raise InvalidCredentialsException()
        if not user.is_active:
            logger.error(f"Login failed - Inactive user: {user.username}")
            raise serializers.ValidationError(UserMessage.USER_INACTIVE)
        logger.debug(f"User authenticated successfully: {user.username}")
        return {"user": user}


class ChangePasswordSerializer(serializers.Serializer):
    """
    Serializer for user password change functionality.

    This serializer handles password change process including:
    - Old password field for verification
    - New password field for update
    - Write-only fields for security

    Provides secure password change capability with proper field protection.
    """

    old_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True)


class UpdateProfileSerializer(serializers.ModelSerializer):
    """
    Serializer for user profile updates with duplicate checking.

    This serializer handles profile update functionality including:
    - Profile field updates (first_name, last_name, email, mobile_number)
    - Duplicate email and mobile number validation
    - User-specific validation (excluding current user from duplicate checks)
    - Partial updates support

    Ensures data integrity while allowing flexible profile updates.
    """

    class Meta:
        model = User
        fields = ["first_name", "last_name", "email", "mobile_number"]

    def validate_email(self, value):
        """
        Validates email uniqueness for profile updates.
        """
        user = self.context["request"].user
        return UserFieldValidators.validate_email_uniqueness(value, "profile_update", user)

    def validate_mobile_number(self, value):
        """
        Validates mobile number uniqueness for profile updates.
        """
        user = self.context["request"].user
        return UserFieldValidators.validate_mobile_number_uniqueness(value, "profile_update", user)


class StaffRequestSerializer(serializers.ModelSerializer):
    """
    Serializer for staff request data display and management.

    This serializer provides comprehensive staff request information including:
    - Staff request details (status, timestamps, notes)
    - Associated user information through nested UserSerializer
    - Read-only fields for system-managed data

    Used for admin interface to view and manage staff approval requests.
    """

    user = UserSerializer(read_only=True)

    class Meta:
        model = StaffRequest
        fields = [
            "id",
            "user",
            "status",
            "requested_at",
            "processed_at",
            "processed_by",
            "notes",
        ]
        read_only_fields = ["user", "requested_at", "processed_at", "processed_by"]


class StaffRequestApprovalSerializer(serializers.ModelSerializer):
    """
    Serializer for staff request approval and rejection operations.

    This serializer handles staff request processing including:
    - Status updates (approved/rejected)
    - Processing notes and comments
    - Field validation for approval operations

    Used by admin users to approve or reject staff registration requests.
    """

    class Meta:
        model = StaffRequest
        fields = ["status", "notes"]
