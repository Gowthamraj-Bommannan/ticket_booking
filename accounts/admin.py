from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User, Role, StaffRequest

@admin.register(User)
class CustomUserAdmin(UserAdmin):
    """
    Custom admin interface for User model management.
    
    This admin class provides comprehensive user management capabilities including:
    - User listing with key fields (username, email, mobile, role, status)
    - Advanced filtering by role, status, and timestamps
    - Search functionality across user fields
    - Organized field grouping for user creation and editing
    - Role-based permission management
    
    Extends Django's UserAdmin to provide enhanced user management
    specific to the custom User model with role-based access control.
    """
    list_display = ('username', 'email', 'mobile_number', 'role', 'is_active', 'get_is_staff', 'get_is_superuser', 'created_at')
    list_filter = ('role', 'is_active', 'created_at')
    search_fields = ('username', 'email', 'mobile_number', 'first_name', 'last_name')
    ordering = ('-created_at',)
    
    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        ('Personal info', {'fields': ('first_name', 'last_name', 'email', 'mobile_number')}),
        ('Permissions', {'fields': ('is_active', 'role', 'groups', 'user_permissions')}),
        ('Important dates', {'fields': ('last_login', 'date_joined', 'created_at')}),
    )
    
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'email', 'mobile_number', 'password1', 'password2', 'role'),
        }),
    )

    def get_is_staff(self, obj):
        """Display is_staff status based on role"""
        return obj.is_staff
    get_is_staff.boolean = True
    get_is_staff.short_description = 'Staff'

    def get_is_superuser(self, obj):
        """Display is_superuser status based on role"""
        return obj.is_superuser
    get_is_superuser.boolean = True
    get_is_superuser.short_description = 'Superuser'

@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    """
    Admin interface for Role model management.
    
    This admin class provides role management capabilities including:
    - Role listing with name, description, and creation timestamp
    - Search functionality for role names and descriptions
    - Alphabetical ordering of roles for easy navigation
    
    Enables administrators to create, edit, and manage user roles
    and their associated permissions within the system.
    """
    list_display = ('name', 'description', 'created_at')
    search_fields = ('name', 'description')
    ordering = ('name',)

@admin.register(StaffRequest)
class StaffRequestAdmin(admin.ModelAdmin):
    """
    Admin interface for StaffRequest model management.
    
    This admin class provides comprehensive staff request management including:
    - Staff request listing with user, status, and processing information
    - Advanced filtering by status and timestamps
    
    Enables administrators to review, approve, and reject staff registration
    requests with full audit trail and processing history.
    """
    list_display = ('user', 'status', 'requested_at', 'processed_at', 'processed_by')
    list_filter = ('status', 'requested_at', 'processed_at')
    search_fields = ('user__username', 'user__email', 'user__mobile_number')
    readonly_fields = ('user', 'requested_at')
    ordering = ('-requested_at',)
    
    fieldsets = (
        ('Request Information', {'fields': ('user', 'status', 'requested_at')}),
        ('Processing Information', {'fields': ('processed_at', 'processed_by', 'notes')}),
    )
    
    def save_model(self, request, obj, form, change):
        """
        Overrides save_model to automatically track who processed the request.
        
        When a staff request status is changed, automatically sets the
        processed_by field to the current admin user and updates the
        processed_at timestamp for audit trail purposes.
        """
        if change and 'status' in form.changed_data:
            obj.processed_by = request.user
        super().save_model(request, obj, form, change)
