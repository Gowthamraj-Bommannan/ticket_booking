from django.db import models
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.utils import timezone

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

class CustomUserManager(BaseUserManager):
    """
    Custom user manager that handles user creation without setting is_staff/is_superuser.
    """
    def create_user(self, username, email=None, password=None, **extra_fields):
        """
        Create and save a user with the given username, email, and password.
        """
        if not username:
            raise ValueError('The given username must be set')
        email = self.normalize_email(email)
        username = self.model.normalize_username(username)
        user = self.model(username=username, email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, username, email=None, password=None, **extra_fields):
        """
        Create and save a superuser with the given username, email, and password.
        """
        extra_fields.setdefault('role', 'admin')
        extra_fields.setdefault('is_active', True)
        
        if extra_fields.get('role') != 'admin':
            raise ValueError('Superuser must have role=admin.')
        
        return self.create_user(username, email, password, **extra_fields)

class User(AbstractUser):
    """
    Custom user model extending Django's AbstractUser for enhanced functionality.
    
    This model provides comprehensive user management including:
    - Extended user fields (email, mobile_number, role)
    - Role-based access control with predefined choices
    - Automatic staff and superuser status based on role
    
    Supports three main user types: admin, user, and station_master with
    appropriate permission levels for each role.
    """
    ROLE_CHOICES = [
        ('admin', 'Admin'),
        ('user', 'User'),
        ('station_master', 'Station Master'),
    ]
    
    email = models.EmailField(unique=True)
    mobile_number = models.CharField(max_length=15, unique=True)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='user')
    created_at = models.DateTimeField(default=timezone.now)
    last_login = models.DateTimeField(blank=True, null=True)

    REQUIRED_FIELDS = ['email', 'mobile_number']
    USERNAME_FIELD = 'username'
    
    objects = CustomUserManager()

    def save(self, *args, **kwargs):
        """
        Overrides the default save method to ensure created_at timestamp is set.
        """
        if not self.created_at:
            self.created_at = timezone.localtime(timezone.now())
        super().save(*args, **kwargs)

    @property
    def is_staff(self):
        """
        Returns True if user has staff privileges based on role.
        """
        return self.role in ['admin', 'station_master']

    @property
    def is_superuser(self):
        """
        Returns True if user has superuser privileges based on role.
        """
        return self.role == 'admin'

    def __str__(self):
        """
        Returns the username and role as the string representation.
        
        Returns:
            str: Username and role in format "username (role)"
        """
        return f"{self.username} ({self.role})"

class StaffRequest(models.Model):
    """
    Model for managing staff registration approval workflow.
    
    This model handles the complete staff approval process including:
    - Staff request creation for new staff registrations
    - Request status tracking (pending, approved, rejected)
    
    Provides a comprehensive audit trail for staff approval decisions
    and supports the complete staff onboarding workflow.
    """
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ]
    
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='staff_request')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    requested_at = models.DateTimeField(auto_now_add=True)
    processed_at = models.DateTimeField(null=True, blank=True)
    processed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='processed_requests')
    notes = models.TextField(blank=True)
    
    def __str__(self):
        """
        Returns the staff request description as the string representation.
        """
        return f"Staff request for {self.user.username} - {self.status}"
