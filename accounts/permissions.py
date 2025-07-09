from rest_framework import permissions

class IsAdminUser(permissions.BasePermission):
    """
    Custom permission class to restrict access to admin users only.
    
    This permission class ensures that only users with superuser privileges
    can access protected views and endpoints. Used for administrative functions
    that require the highest level of system access and control.
    
    Extends Django REST Framework's BasePermission to provide custom
    authentication and authorization logic for admin-only operations.
    """
    def has_permission(self, request, view):
        """
        Determines if the requesting user has admin permissions.
        
        Checks if the user is authenticated and has superuser privileges.
        Returns True only for users with full administrative access.
        
        Args:
            request: The HTTP request object
            view: The view being accessed
            
        Returns:
            bool: True if user is authenticated and is a superuser, False otherwise
        """
        return bool(request.user and request.user.is_authenticated and request.user.is_superuser)

class IsStaffOrAdmin(permissions.BasePermission):
    """
    Custom permission class to restrict access to staff or admin users.
    
    This permission class allows access to users with either staff privileges
    or full admin privileges. Used for operations that require elevated
    permissions but not necessarily full administrative access.
    
    Provides flexible access control for staff-level operations while
    maintaining security for sensitive administrative functions.
    """
    def has_permission(self, request, view):
        """
        Determines if the requesting user has staff or admin permissions.
        
        Checks if the user is authenticated and has either staff or superuser
        privileges. Returns True for users with elevated access levels.
        
        Args:
            request: The HTTP request object
            view: The view being accessed
            
        Returns:
            bool: True if user is authenticated and has staff or superuser privileges, False otherwise
        """
        return bool(request.user and request.user.is_authenticated and (request.user.is_staff or request.user.is_superuser))

class IsOwnerOrAdmin(permissions.BasePermission):
    """
    Custom permission class to restrict access to object owners or admin users.
    
    This permission class implements object-level permissions allowing users
    to access only their own data while granting full access to administrators.
    Used for user-specific operations like profile management and personal data access.
    
    Provides secure access control ensuring users can only modify their own
    information while maintaining administrative oversight capabilities.
    """
    def has_object_permission(self, request, view, obj):
        """
        Determines if the requesting user has permission to access a specific object.
        
        Checks if the user is a superuser (full access) or if the object belongs
        to the requesting user. Supports objects with 'user' attribute or direct
        ID matching for user objects.
        
        Args:
            request: The HTTP request object
            view: The view being accessed
            obj: The object being accessed
            
        Returns:
            bool: True if user is admin or object owner, False otherwise
        """
        # Admin can access any object
        if request.user.is_superuser:
            return True
        
        # Check if the object has a user attribute
        if hasattr(obj, 'user'):
            return obj.user == request.user
        elif hasattr(obj, 'id'):
            return obj.id == request.user.id
        
        return False 