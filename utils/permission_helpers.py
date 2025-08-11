from rest_framework import permissions


class RoleBasedPermissions:
    """
    Reusable permission classes to eliminate code duplication.
    """
    
    @staticmethod
    def has_role(request, allowed_roles):
        """
        Generic role-based permission check.
        
        Args:
            request: HTTP request object
            allowed_roles (list): List of allowed role names
            
        Returns:
            bool: True if user has one of the allowed roles
        """
        if not request.user or not request.user.is_authenticated:
            return False
        
        if not request.user.role:
            return False
            
        return request.user.role.name in allowed_roles


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
        return RoleBasedPermissions.has_role(request, ["admin"])


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
        return RoleBasedPermissions.has_role(request, ["admin", "station_master"])


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
            bool: True if user has permission to access the object, False otherwise
        """
        # Admin users have full access
        if RoleBasedPermissions.has_role(request, ["admin"]):
            return True

        # Check if object belongs to the requesting user
        if hasattr(obj, "user"):
            return obj.user == request.user
        elif hasattr(obj, "id"):
            return obj.id == request.user.id

        return False


class DynamicPermissionMixin:
    """
    Mixin to provide dynamic permission handling based on request method.

    This mixin allows different permission classes for different HTTP methods,
    providing fine-grained access control for different operations on the same endpoint.
    """

    def get_permissions(self):
        """
        Returns permission classes based on request method.

        Provides different permissions for different HTTP methods:
        - GET: AllowAny for public data, IsAuthenticated for private data
        - POST/PUT/PATCH/DELETE: IsAuthenticated for all operations

        Returns:
            list: List of permission classes for the current request method
        """
        if self.request.method == "GET":
            return [permissions.AllowAny()]
        return [permissions.IsAuthenticated()]


class AdminOnlyPermissionMixin:
    """
    Mixin to restrict access to admin users only.

    This mixin ensures that only users with admin role can access the view,
    providing administrative-level access control.
    """

    def get_permissions(self):
        """
        Returns admin-only permission classes.

        Returns:
            list: List containing IsAdminUser permission class
        """
        return [IsAdminUser()]


class UserSpecificPermissionMixin:
    """
    Mixin to restrict access to object owners or admin users.

    This mixin provides object-level permissions allowing users to access
    only their own data while granting full access to administrators.
    """

    def get_permissions(self):
        """
        Returns user-specific permission classes.

        Returns:
            list: List containing IsOwnerOrAdmin permission class
        """
        return [IsOwnerOrAdmin()]


class StaffOrAdminPermissionMixin:
    """
    Mixin to restrict access to staff or admin users.

    This mixin allows access to users with either station_master role
    or admin role, providing elevated permission levels.
    """

    def get_permissions(self):
        """
        Returns staff or admin permission classes.

        Returns:
            list: List containing IsStaffOrAdmin permission class
        """
        return [IsStaffOrAdmin()] 