from django.db import models
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.utils import timezone
from utils.constants import Choices


class Role(models.Model):
    """
    Model for defining user roles and permissions in the system.

    This model provides a flexible role-based access control system allowing
    administrators to define custom roles with specific permissions and descriptions.
    Each role can be assigned to users to control their access levels and capabilities.
    """

    name = models.CharField(max_length=50, unique=True)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        """
        Returns the role name as the string representation.

        Returns:
            str: The name of the role
        """
        return self.name


class UserOTPVerification(models.Model):
    """
    Model for managing OTP verification during user registration.
    
    This model handles the complete OTP verification process including:
    - OTP generation and storage
    - Expiry time management
    - Attempt tracking
    - Verification status
    """
    email = models.EmailField()
    otp_code = models.CharField(max_length=6)
    expiry_time = models.DateTimeField()
    attempt_count = models.IntegerField(default=0)
    is_verified = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "otp_verification"
    
    def __str__(self):
        """
        Returns the OTP verification description as the string representation.
        """
        return f"OTP for {self.email} - {'Verified' if self.is_verified else 'Pending'}"
    
    @property
    def is_expired(self):
        """
        Check if OTP has expired.
        """
        return timezone.now() > self.expiry_time


class CustomUserManager(BaseUserManager):
    """
    Custom user manager that handles user creation without setting is_staff/is_superuser.
    """

    def create_user(self, username, email=None, password=None, **extra_fields):
        """
        Create and save a user with the given username, email, and password.
        Validation is handled by serializers, this method focuses on user creation.
        """
        if not username:
            raise ValueError("The given username must be set")
        email = self.normalize_email(email)
        username = self.model.normalize_username(username)
        
        user = self.model(username=username, email=email, **extra_fields)
        user.set_password(password)
        user.save()
        return user

    def create_superuser(self, username, email=None, password=None, **extra_fields):
        """
        Create and save a superuser with the given username, email, and password.
        """
        extra_fields.setdefault("is_active", True)

        return self.create_user(username, email, password, **extra_fields)


class User(AbstractUser):
    """
    Custom user model extending Django's AbstractUser for enhanced functionality.

    This model provides comprehensive user management including:
    - Extended user fields (email, mobile_number, role)
    - Role-based access control with ForeignKey to Role model
    - Automatic staff and superuser status based on role
    - Approval system for staff users

    Supports three main user types: admin, user, and station_master with
    appropriate permission levels for each role.
    """
    email = models.EmailField()
    mobile_number = models.CharField(max_length=15)
    role = models.ForeignKey(Role, on_delete=models.CASCADE, null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now)
    last_login = models.DateTimeField(blank=True, null=True)

    REQUIRED_FIELDS = ["email", "mobile_number"]
    USERNAME_FIELD = "username"

    objects = CustomUserManager()

    class Meta:
        db_table = "users"

    @property
    def is_staff(self):
        """
        Returns True if user has staff privileges based on role.
        """
        if not self.role:
            return False
        return self.role.name in ["admin", "station_master"]

    @property
    def is_superuser(self):
        """
        Returns True if user has superuser privileges based on role.
        """
        if not self.role:
            return False
        return self.role.name == "admin"

    def __str__(self):
        """
        Returns the username and role as the string representation.

        Returns:
            str: Username and role in format "username (role)"
        """
        role_name = self.role.name if self.role else "No Role"
        return f"{self.username} ({role_name})"


class StaffRequest(models.Model):
    """
    Model for managing staff registration approval workflow.

    This model handles the complete staff approval process including:
    - Staff request creation for new staff registrations
    - Request status tracking (pending, approved, rejected)

    Provides a comprehensive audit trail for staff approval decisions
    and supports the complete staff onboarding workflow.
    """
    user = models.OneToOneField(
       User, on_delete=models.CASCADE, related_name="staff_request"
    )
    status = models.CharField(max_length=20, choices=Choices.STATUS_CHOICES, default="pending")
    requested_at = models.DateTimeField(auto_now_add=True)
    processed_at = models.DateTimeField(null=True, blank=True)
    processed_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="processed_requests",
    )
    notes = models.TextField(blank=True)

    class Meta:
        db_table = "staff_requests"

    def __str__(self):
        """
        Returns the staff request description as the string representation.
        """
        return f"Staff request for {self.user.username} - {self.status}"
