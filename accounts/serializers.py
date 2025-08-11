from rest_framework import serializers
from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from .models import User, StaffRequest, Role, UserOTPVerification
from utils.constants import UserMessage, AlreadyExistsMessage
from utils.validators import UserFieldValidators
from exceptions.handlers import InvalidInputException

class RoleSerializer(serializers.ModelSerializer):
    """Serializer for Role model."""
    
    class Meta:
        model = Role
        fields = ['id', 'name', 'description']


class RegistrationSerializer(serializers.ModelSerializer):
    """
    Unified serializer for both user and staff registration.
    
    This serializer handles validation for unified registration including:
    - Data validation for all registration fields
    - Duplicate email and mobile number checking
    - Field format and constraint validation
    - Role-based registration logic
    """
    role_id = serializers.IntegerField(required=True, help_text="Role ID from the Role table")
    password = serializers.CharField(write_only=True, min_length=8)

    class Meta:
        model = User
        fields = [
            'username', 'email', 'mobile_number', 'password',
            'first_name', 'last_name', 'role_id'
        ]

    def validate_email(self, value):
        """
        Validates email uniqueness for unified registration.
        """
        return UserFieldValidators.validate_email_uniqueness(value)

    def validate_mobile_number(self, value):
        """
        Validates mobile number format and uniqueness for unified registration.
        """
        if not value.isdigit() or len(value) < 10:
            raise InvalidInputException(UserMessage.MOBILE_NUMBER_INVALID)
        
        return UserFieldValidators.validate_mobile_number_uniqueness(value)
    
    def validate_username(self, value):
        """
        Validates username format and uniqueness for unified registration.
        """
        if len(value) < 5:
            raise InvalidInputException(UserMessage.USERNAME_TOO_SHORT)
        
        return UserFieldValidators.validate_username_uniqueness(value)

    def validate_role_id(self, value):
        """
        Validates that the role_id exists and is valid.
        """
        try:
            role = Role.objects.get(id=value)
            if role.name == "admin":
                raise InvalidInputException(UserMessage.ADMIN_ROLE_REGISTRATION_NOT_ALLOWED)
            return value
        except Role.DoesNotExist:
            raise InvalidInputException(UserMessage.ROLE_NOT_FOUND)

    def validate(self, data):
        """
        Validates password confirmation.
        """
        password = data.get('password')
        confirm_password = data.get('confirm_password')
        
        if password and confirm_password and password != confirm_password:
            raise InvalidInputException(UserMessage.PASSWORD_NOT_MATCH)
        
        return data


class OTPValidationSerializer(serializers.Serializer):
    """
    Serializer for OTP validation.
    """
    email = serializers.EmailField()
    otp_code = serializers.CharField(max_length=6, min_length=6)


class UserOTPVerificationSerializer(serializers.ModelSerializer):
    """
    Serializer for UserOTPVerification model.
    """
    class Meta:
        model = UserOTPVerification
        fields = ['email', 'otp_code', 'expiry_time', 'attempt_count', 'is_verified', 'created_at']
        read_only_fields = ['expiry_time', 'attempt_count', 'is_verified', 'created_at']


class UserSerializer(serializers.ModelSerializer):
    """
    Serializer for user profile data display and management.

    This serializer provides comprehensive user information including:
    - Basic profile fields (username, email, mobile_number, names)
    - System fields (role, timestamps, active status)
    - Read-only fields for system-managed data

    Used for profile display, user data in responses, and general user information.
    """
    role = RoleSerializer(read_only=True)

    class Meta:
        model = User
        fields = [
            "id",
            "username",
            "email",
            "mobile_number",
            "first_name",
            "last_name",
            "role",
            "is_active",
            "created_at",
            "last_login",
        ]
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
        Validates user authentication credentials.

        Performs comprehensive authentication validation including:
        - User existence and credential verification
        - Account status validation (active/inactive)
        - Custom error messages for different failure scenarios

        Args:
            data: Dictionary containing username and password

        Returns:
            dict: Validated data with authenticated user object

        Raises:
            serializers.ValidationError: For authentication failures
        """
        username = data.get("username")
        password = data.get("password")

        if username and password:
            user = authenticate(username=username, password=password)
            if user:
                if not user.is_active:
                    raise InvalidInputException(UserMessage.INVALID_CREDENTIALS)
                data["user"] = user
                return data
            else:
                raise serializers.ValidationError(
                    UserMessage.INVALID_CREDENTIALS
                )
        else:
            raise serializers.ValidationError(
                UserMessage.INVALID_CREDENTIALS
            )


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

    def validate_new_password(self, value):
        """
        Validates new password using Django's password validators.

        Ensures password meets security requirements and provides
        appropriate error messages for validation failures.

        Args:
            value: New password string

        Returns:
            str: Validated password

        Raises:
            serializers.ValidationError: For password validation failures
        """
        validate_password(value)
        return value


class UpdateProfileSerializer(serializers.ModelSerializer):
    """
    Serializer for user profile updates.

    This serializer handles profile update functionality including:
    - Partial updates for profile fields
    - Unique constraint validation for email and mobile number
    - Field format validation

    Provides secure profile update capability with proper validation.
    """

    class Meta:
        model = User
        fields = ["first_name", "last_name", "email", "mobile_number"]

    def validate_email(self, value):
        """
        Validates email uniqueness for profile updates.

        Ensures email is unique across all users except the current user
        being updated.

        Args:
            value: Email address to validate

        Returns:
            str: Validated email address

        Raises:
            serializers.ValidationError: For duplicate email addresses
        """
        return UserFieldValidators.validate_email_uniqueness(value)

    def validate_mobile_number(self, value):
        """
        Validates mobile number uniqueness for profile updates.

        Ensures mobile number is unique across all users except the current user
        being updated.

        Args:
            value: Mobile number to validate

        Returns:
            str: Validated mobile number

        Raises:
            serializers.ValidationError: For duplicate mobile numbers
        """
        return UserFieldValidators.validate_mobile_number_uniqueness(value)


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
    Serializer for staff request approval operations.

    This serializer handles staff request approval functionality including:
    - Status field for approval/rejection
    - Notes field for admin comments
    - Validation for status transitions

    Used for admin approval and rejection operations.
    """

    class Meta:
        model = StaffRequest
        fields = ["status", "notes"]
