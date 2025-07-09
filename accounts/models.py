from django.db import models
from django.contrib.auth.models import AbstractUser
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
    
    # Override AbstractUser fields
    is_staff = models.BooleanField(default=False)
    is_superuser = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    REQUIRED_FIELDS = ['email', 'mobile_number']
    USERNAME_FIELD = 'username'

    def save(self, *args, **kwargs):
        """
        Overrides the default save method to set role-based permissions.
        
        Automatically sets is_staff and is_superuser flags based on the user's role:
        - Admin: Full staff and superuser privileges
        - Station Master: Staff privileges only
        - User: No special privileges
        
        Also ensures created_at timestamp is set for new users.
        
        Args:
            *args: Additional positional arguments
            **kwargs: Additional keyword arguments
        """
        if not self.created_at:
            self.created_at = timezone.localtime(timezone.now())
        
        # Set is_staff and is_superuser based on role
        if self.role == 'admin':
            self.is_staff = True
            self.is_superuser = True
        elif self.role == 'station_master':
            self.is_staff = True
            self.is_superuser = False
        else:  # user
            self.is_staff = False
            self.is_superuser = False
            
        super().save(*args, **kwargs)

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
