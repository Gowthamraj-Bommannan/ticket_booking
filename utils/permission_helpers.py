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
            allowed_roles (list): List of allowed roles
            
        Returns:
            bool: True if user has one of the allowed roles
        """
        return bool(
            request.user
            and request.user.is_authenticated
            and getattr(request.user, "role", None) in allowed_roles
        )


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
            bool: True if user is admin or object owner, False otherwise
        """
        # Admin can access any object
        if getattr(request.user, "role", None) == "admin":
            return True

        # Check if the object has a user attribute
        if hasattr(obj, "user"):
            return obj.user == request.user
        elif hasattr(obj, "id"):
            return obj.id == request.user.id

        return False


# Alias for backward compatibility - both classes are identical
IsStationMasterOrAdmin = IsStaffOrAdmin


# New Permission Mixins for Dynamic Permissions
class DynamicPermissionMixin:
    """
    Mixin to provide dynamic permission handling based on actions.
    Reduces code duplication across ViewSets.
    """
    
    def get_permissions(self):
        """
        Returns appropriate permissions based on the action.
        Override this method in subclasses to customize permission logic.
        """
        if self.action in ["create", "update", "partial_update", "destroy"]:
            permission_classes = [IsAdminUser]
        elif self.action in ["deactivate", "activate"]:
            permission_classes = [IsStaffOrAdmin]
        else:
            permission_classes = [permissions.IsAuthenticated]
        return [permission() for permission in permission_classes]


class AdminOnlyPermissionMixin:
    """
    Mixin for views that require admin-only access for all actions.
    """
    
    def get_permissions(self):
        return [IsAdminUser()]


class UserSpecificPermissionMixin:
    """
    Mixin for views that allow users to access only their own data.
    """
    
    def get_permissions(self):
        return [IsOwnerOrAdmin()]


class StaffOrAdminPermissionMixin:
    """
    Mixin for views that allow both staff and admin access.
    """
    
    def get_permissions(self):
        return [IsStaffOrAdmin()] 