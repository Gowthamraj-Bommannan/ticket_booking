from rest_framework import serializers
from django.contrib.auth import authenticate
from .models import User, StaffRequest
from django.utils import timezone
from rest_framework_simplejwt.tokens import RefreshToken
from exceptions.handlers import DuplicateEmailException, MobileNumberAlreadyExists, InvalidCredentialsException
from utils.constants import AlreadyExistsMessage, UserMessage
import logging

logger = logging.getLogger("accounts")

class RegisterSerializer(serializers.ModelSerializer):
    """
    Serializer for user registration validation.
    
    This serializer handles validation for user registration including:
    - Data validation for all registration fields
    - Duplicate email and mobile number checking
    - Field format and constraint validation
    
    Provides comprehensive validation for user registration data.
    """
    email = serializers.EmailField(validators=[])
    username = serializers.CharField(validators=[])
    mobile_number = serializers.CharField(validators=[])
    password = serializers.CharField(write_only=True)
    
    class Meta:
        model = User
        fields = ['username', 'email', 'mobile_number', 'password', 'first_name', 'last_name']

    def validate_email(self, value):
        """
        Validates email uniqueness for user registration.
        
        Checks if the provided email address is already registered in the system.
        Raises DuplicateEmailException if email already exists.
        
        Args:
            value (str): The email address to validate
            
        Returns:
            str: The validated email address
            
        Raises:
            DuplicateEmailException: If email already exists in the system
        """
        if User.objects.filter(email=value).exists():
            logger.warning(f"Registration failed - Email already exists: {value}")
            raise DuplicateEmailException()
        return value

    def validate_mobile_number(self, value):
        """
        Validates mobile number uniqueness for user registration.
        
        Checks if the provided mobile number is already registered in the system.
        Raises MobileNumberAlreadyExists if mobile number already exists.
        
        Args:
            value (str): The mobile number to validate
            
        Returns:
            str: The validated mobile number
            
        Raises:
            MobileNumberAlreadyExists: If mobile number already exists in the system
        """
        if User.objects.filter(mobile_number=value).exists():
            logger.warning(f"Registration failed - Mobile number already exists: {value}")
            raise MobileNumberAlreadyExists()
        # Add mobile number validation logic here (e.g., regex, OTP, etc.)
        return value

class StaffRegisterSerializer(serializers.ModelSerializer):
    """
    Serializer for staff registration validation.
    
    This serializer handles validation for staff registration including:
    - Data validation for all registration fields
    - Duplicate email and mobile number checking
    - Field format and constraint validation
    
    Provides comprehensive validation for staff registration data.
    """
    email = serializers.EmailField(validators=[])
    username = serializers.CharField(validators=[])
    mobile_number = serializers.CharField(validators=[])
    password = serializers.CharField(write_only=True)
    
    class Meta:
        model = User
        fields = ['username', 'email', 'mobile_number', 'password', 'first_name', 'last_name']

    def validate_email(self, value):
        """
        Validates email uniqueness for staff registration.
        
        Checks if the provided email address is already registered in the system.
        Raises DuplicateEmailException if email already exists.
        
        Args:
            value (str): The email address to validate
            
        Returns:
            str: The validated email address
            
        Raises:
            DuplicateEmailException: If email already exists in the system
        """
        if User.objects.filter(email=value).exists():
            logger.warning(f"Staff registration failed - Email already exists: {value}")
            raise DuplicateEmailException()
        return value

    def validate_mobile_number(self, value):
        """
        Validates mobile number uniqueness for staff registration.
        
        Checks if the provided mobile number is already registered in the system.
        Raises MobileNumberAlreadyExists if mobile number already exists.
        
        Args:
            value (str): The mobile number to validate
            
        Returns:
            str: The validated mobile number
            
        Raises:
            MobileNumberAlreadyExists: If mobile number already exists in the system
        """
        if User.objects.filter(mobile_number=value).exists():
            logger.warning(f"Staff registration failed - Mobile number already exists: {value}")
            raise MobileNumberAlreadyExists()
        return value

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
        fields = ['id', 'username', 'email', 'first_name', 'role']
        read_only_fields = ['role', 'created_at', 'last_login', 'is_active']

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
        
        Args:
            data (dict): Dictionary containing username and password
            
        Returns:
            dict: Dictionary containing the authenticated user object
            
        Raises:
            InvalidCredentialsException: If username/password combination is invalid
            ValidationError: If user account is inactive
        """
        user = authenticate(username=data['username'], password=data['password'])
        if not user:
            logger.warning(f"Login failed - Invalid credentials for username: {data['username']}")
            raise InvalidCredentialsException()
        if not user.is_active:
            logger.warning(f"Login failed - Inactive user: {user.username}")
            raise serializers.ValidationError(UserMessage.USER_INACTIVE)
        logger.debug(f"User authenticated successfully: {user.username}")
        return {'user': user}

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
        fields = ['first_name', 'last_name', 'email', 'mobile_number']

    def validate_email(self, value):
        """
        Validates email uniqueness for profile updates.
        
        Checks if the provided email address is already registered by another user.
        Excludes the current user from duplicate checking to allow keeping same email.
        Raises DuplicateEmailException if email already exists for another user.
        
        Args:
            value (str): The email address to validate
            
        Returns:
            str: The validated email address
            
        Raises:
            DuplicateEmailException: If email already exists for another user
        """
        user = self.context['request'].user
        if User.objects.exclude(pk=user.pk).filter(email=value).exists():
            logger.warning(f"Profile update failed - Email already exists: {value} for user: {user.username}")
            raise DuplicateEmailException()
        return value

    def validate_mobile_number(self, value):
        """
        Validates mobile number uniqueness for profile updates.
        
        Checks if the provided mobile number is already registered by another user.
        Excludes the current user from duplicate checking to allow keeping same mobile number.
        Raises MobileNumberAlreadyExists if mobile number already exists for another user.
        
        Args:
            value (str): The mobile number to validate
            
        Returns:
            str: The validated mobile number
            
        Raises:
            MobileNumberAlreadyExists: If mobile number already exists for another user
        """
        user = self.context['request'].user
        if User.objects.exclude(pk=user.pk).filter(mobile_number=value).exists():
            logger.warning(f"Profile update failed - Mobile number already exists: {value} for user: {user.username}")
            raise MobileNumberAlreadyExists()
        return value

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
        fields = ['id', 'user', 'status', 'requested_at', 'processed_at', 'processed_by', 'notes']
        read_only_fields = ['user', 'requested_at', 'processed_at', 'processed_by']

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
        fields = ['status', 'notes']