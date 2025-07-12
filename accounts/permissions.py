from rest_framework import permissions

class IsAdminUser(permissions.BasePermission):
    """
    Custom permission class to restrict access to admin users only.
    
    This permission class ensures that only users with admin role
    can access protected views and endpoints. Used for administrative functions
    that require the highest level of system access and control.
    """
    def has_permission(self, request, view):
        """
        Determines if the requesting user has admin permissions.
        
        Checks if the user is authenticated and has admin role.
        Returns True only for users with full administrative access.
        
        Args:
            request: The HTTP request object
            view: The view being accessed
            
        Returns:
            bool: True if user is authenticated and has admin role, False otherwise
        """
        return bool(request.user and request.user.is_authenticated and request.user.role == 'admin')

class IsStaffOrAdmin(permissions.BasePermission):
    """
    Custom permission class to restrict access to staff or admin users.
    
    This permission class allows access to users with either station_master role
    or admin role. Used for operations that require elevated permissions
    but not necessarily full administrative access.
    """
    def has_permission(self, request, view):
        """
        Determines if the requesting user has staff or admin permissions.
        
        Checks if the user is authenticated and has either station_master or admin role.
        Returns True for users with elevated access levels.
        
        Args:
            request: The HTTP request object
            view: The view being accessed
            
        Returns:
            bool: True if user is authenticated and has staff or admin role, False otherwise
        """
        return bool(request.user and request.user.is_authenticated and request.user.role in ['admin', 'station_master'])

class IsOwnerOrAdmin(permissions.BasePermission):
    """
    Custom permission class to restrict access to object owners or admin users.
    
    This permission class implements object-level permissions allowing users
    to access only their own data while granting full access to administrators.
    Used for user-specific operations like profile management and personal data access.
    """
    def has_object_permission(self, request, view, obj):
        """
        Determines if the requesting user has permission to access a specific object.
        
        Checks if the user is an admin (full access) or if the object belongs
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
        if request.user.role == 'admin':
            return True
        
        # Check if the object has a user attribute
        if hasattr(obj, 'user'):
            return obj.user == request.user
        elif hasattr(obj, 'id'):
            return obj.id == request.user.id
        
        return False

class IsStationMasterOrAdmin(permissions.BasePermission):
    """
    Custom permission class to restrict access to station masters or admin users.
    
    This permission class allows access to users with station_master role
    or admin role. Used for station-specific operations.
    """
    def has_permission(self, request, view):
        """
        Determines if the requesting user has station master or admin permissions.
        
        Args:
            request: The HTTP request object
            view: The view being accessed
            
        Returns:
            bool: True if user is authenticated and has station_master or admin role, False otherwise
        """
        return bool(request.user and request.user.is_authenticated and request.user.role in ['admin', 'station_master']) 