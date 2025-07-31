from django.shortcuts import get_object_or_404
from rest_framework import generics, permissions
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView
from django.contrib.auth import get_user_model, update_session_auth_hash
from django.contrib.auth.password_validation import validate_password
from django.utils import timezone
from .serializers import (
    RegisterSerializer,
    StaffRegisterSerializer,
    LoginSerializer,
    UserSerializer,
    ChangePasswordSerializer,
    UpdateProfileSerializer,
    StaffRequestSerializer,
)
from rest_framework.permissions import IsAuthenticated
from .models import StaffRequest
import logging
from utils.permission_helpers import IsAdminUser
from bookingsystem.models import Booking
from bookingsystem.serializers import BookingSerializer
from rest_framework.decorators import api_view, permission_classes
from rest_framework.exceptions import ValidationError as DRFValidationError
from exceptions.handlers import (
    InvalidCredentialsException,
    AlreadyExistsException,
    InvalidInputException,
    UnauthorizedAccessException,
    NotFoundException,
)
from utils.constants import (UserMessage, GeneralMessage,
                             AlreadyExistsMessage)
from utils.registration_helpers import RegistrationFlowHelper

User = get_user_model()
logger = logging.getLogger("accounts")


class RegisterView(APIView):
    """
    Handles user registration with OTP verification.

    This view manages the complete user registration process including:
    - Initial registration data validation
    - OTP sending and verification
    - User account creation
    - JWT token generation for immediate login

    Supports a two-step registration process:
    1. First request: Validates data and sends OTP
    2. Second request: Verifies OTP and creates user account
    """

    permission_classes = [permissions.AllowAny]

    def post(self, request):
        """
        Processes user registration requests.

        Handles both initial registration (sends OTP) and final
        registration (verifies OTP).
        Creates user account with 'user' role upon successful OTP verification

        Args:
            request: HTTP request object containing registration data

        Returns:
            Response: Success response with tokens and user data, or
            OTP sent confirmation
        """
        serializer = RegisterSerializer(data=request.data)
        try:
            serializer.is_valid(raise_exception=True)
            return RegistrationFlowHelper.handle_registration_request(
                request, serializer, "registration"
                )
        
        except (InvalidInputException, AlreadyExistsException, DRFValidationError) as e:
            return RegistrationFlowHelper.handle_registration_error(
                e, serializer, "registration")
        
        except Exception as e:
            logger.error(f"Unexpected error during registration: {str(e)}", exc_info=True)
            return RegistrationFlowHelper.handle_registration_error(
                e, serializer, "registration")




class StaffRegisterView(APIView):
    """
    Handles staff registration with OTP verification and approval workflow.

    This view manages staff registration process including:
    - Initial registration data validation
    - OTP sending and verification
    - Staff user account creation with 'station_master' role
    - Staff request creation for admin approval
    - Account remains inactive until admin approval

    Supports a two-step registration process similar to regular registration.
    """

    permission_classes = [permissions.AllowAny]

    def post(self, request):
        """
        Processes staff registration requests.

        Handles both initial registration (sends OTP) and final registration
        (verifies OTP). Creates staff user account with 'station_master' 
        role and creates approval request.

        Args:
            request: HTTP request object containing staff registration data

        Returns:
            Response: Success response with approval status, or OTP sent
            confirmation
        """
        serializer = StaffRegisterSerializer(data=request.data)
        try:
            serializer.is_valid(raise_exception=True)
            return RegistrationFlowHelper.handle_registration_request(
                request, serializer, "staff_registration"
                )
        except (InvalidInputException, AlreadyExistsException, DRFValidationError) as e:
            return RegistrationFlowHelper.handle_registration_error(
                e, serializer, "staff_registration"
                )
        except Exception as e:
            logger.error(
                f"Unexpected error during registration: {str(e)}",
                exc_info=True)
            return RegistrationFlowHelper.handle_registration_error(e, serializer, "staff_registration")




class LoginView(TokenObtainPairView):
    """
    Handles user authentication and JWT token generation.

    This view extends Django REST Framework's TokenObtainPairView to provide:
    - Username and password authentication
    - JWT access and refresh token generation
    - Last login timestamp update
    - User data serialization in response

    Supports standard JWT authentication flow with custom user data inclusion.
    """

    serializer_class = LoginSerializer
    permission_classes = [permissions.AllowAny]

    def post(self, request, *args, **kwargs):
        """
        Processes user login requests.

        Authenticates user credentials, generates JWT tokens, updates last login,
        and returns user data along with access and refresh tokens.

        Args:
            request: HTTP request object containing login credentials
            *args: Additional positional arguments
            **kwargs: Additional keyword arguments

        Returns:
            Response: Success response with JWT tokens and user data
        """
        serializer = self.get_serializer(data=request.data)
        try:
            serializer.is_valid(raise_exception=True)
            user = serializer.validated_data["user"]
            user.last_login = timezone.localtime(timezone.now())
            user.save(update_fields=["last_login"])
            refresh = RefreshToken.for_user(user)
            data = {
                "refresh": str(refresh),
                "access": str(refresh.access_token),
                "user": UserSerializer(user).data,
            }
            logger.info(f"User {user.username} (ID: {user.id}) logged in successfully")
            return Response(data)
        except InvalidCredentialsException as e:
            logger.error(f"Login failed - {type(e).__name__}: {str(e)}")
            raise InvalidCredentialsException(UserMessage.INVALID_CREDENTIALS)
        except InvalidInputException as e:
            logger.error(f"Login failed - {type(e).__name__}: {str(e)}")
            raise InvalidInputException(GeneralMessage.INVALID_INPUT)
        except Exception as e:
            logger.error(f"Unexpected error during login: {str(e)}", exc_info=True)
            raise Exception(GeneralMessage.SOMETHING_WENT_WRONG)


class LogoutView(APIView):
    """
    Handles user logout functionality.

    This view provides logout endpoint for client-side token management.
    Since JWT tokens are stateless, actual token invalidation is handled client-side.
    Can be extended to implement token blacklisting if required.
    """

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        """
        Processes user logout requests.

        Logs the logout action for audit purposes. JWT token invalidation
        is typically handled client-side by removing stored tokens.

        Args:
            request: HTTP request object

        Returns:
            Response: Success confirmation message
        """
        logger.info(f"User {request.user.username} (ID: {request.user.id}) logged out")
        return Response({"detail": "Logged out successfully."}, status=200)


class ProfileView(generics.RetrieveUpdateAPIView):
    """
    Handles user profile retrieval and updates.

    This view provides functionality to:
    - Retrieve current user's profile information
    - Update user profile data (first_name, last_name, email, mobile_number)
    - Validate unique constraints for email and mobile number updates

    Supports both GET (retrieve) and PUT (update) operations.
    """

    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        """
        Returns the current authenticated user object.

        Overrides the default get_object method to return the requesting user
        instead of looking up by URL parameters.

        Returns:
            User: The currently authenticated user object
        """
        return self.request.user

    def get(self, request, *args, **kwargs):
        """
        Retrieves current user's profile information.

        Returns serialized user data including profile fields and system information.

        Args:
            request: HTTP request object
            *args: Additional positional arguments
            **kwargs: Additional keyword arguments

        Returns:
            Response: Serialized user profile data
        """
        logger.info(
            f"User {request.user.username} (ID: {request.user.id}) requested profile"
        )
        return super().get(request, *args, **kwargs)

    def put(self, request, *args, **kwargs):
        """
        Updates current user's profile information.

        Validates and updates user profile data including first_name, last_name,
        email, and mobile_number with duplicate checking.

        Args:
            request: HTTP request object containing updated profile data
            *args: Additional positional arguments
            **kwargs: Additional keyword arguments

        Returns:
            Response: Updated user profile data
        """
        serializer = UpdateProfileSerializer(
            self.request.user,
            data=request.data,
            partial=True,
            context={"request": request},
        )
        try:
            serializer.is_valid(raise_exception=True)
            serializer.save()
            logger.info(
                f"User {request.user.username} (ID: {request.user.id}) updated profile successfully"
            )
            return Response(UserSerializer(self.request.user).data)
        except AlreadyExistsException as e:
            logger.error(
                f"Profile update failed for user {request.user.username} - {type(e).__name__}: {str(e)}"
            )
            raise AlreadyExistsException(AlreadyExistsMessage.EMAIL_ALREADY_EXISTS)
        except Exception as e:
            logger.error(
                f"Unexpected error during profile update for user {request.user.username}: {str(e)}",
                exc_info=True,
            )
            raise Exception(GeneralMessage.SOMETHING_WENT_WRONG)


class ChangePasswordView(APIView):
    """
    Handles user password change functionality.

    This view provides secure password change capability including:
    - Current password verification
    - New password validation using Django's password validators
    - Password update and session hash maintenance
    - Comprehensive error handling and logging
    """

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        """
        Processes password change requests.

        Validates current password, ensures new password meets requirements,
        updates user password, and maintains session authentication.

        Args:
            request: HTTP request object containing old and new passwords

        Returns:
            Response: Success confirmation message
        """
        serializer = ChangePasswordSerializer(data=request.data)
        try:
            serializer.is_valid(raise_exception=True)
            user = request.user
            if not user.check_password(serializer.validated_data["old_password"]):
                logger.error(
                    f"Password change failed for user {user.username} - Wrong old password"
                )
                raise InvalidCredentialsException("Wrong password.")
            
            try:
                validate_password(serializer.validated_data["new_password"], user)
            except InvalidInputException:
                logger.error(
                    f"Password validation failed for user {user.username}"
                )
                raise InvalidInputException(GeneralMessage.INVALID_INPUT)
            user.set_password(serializer.validated_data["new_password"])
            user.save()
            update_session_auth_hash(request, user)
            logger.info(
                f"User {user.username} (ID: {user.id}) changed password successfully"
            )
            return Response({"detail": UserMessage.PASSWORD_CHANGED_SUCCESS})
        except InvalidCredentialsException:
            raise InvalidCredentialsException(UserMessage.INVALID_CREDENTIALS)
        except InvalidInputException:
            raise InvalidInputException(GeneralMessage.INVALID_INPUT)
        except Exception:
            logger.error(
                f"Unexpected error during password change for user {request.user.username}",
                exc_info=True,
            )
            raise Exception(GeneralMessage.SOMETHING_WENT_WRONG)


# Admin Approval Panel Views
class StaffRequestListView(generics.ListAPIView):
    """
    Handles listing of pending staff requests for admin approval.
    This view provides admin functionality to view all pending staff registration
    requests that require approval. Only accessible by admin users.
    """

    serializer_class = StaffRequestSerializer
    permission_classes = [IsAdminUser]

    def get_queryset(self):
        """
        Returns filtered queryset of pending staff requests.
        Filters staff requests to show only those with 'pending' status
        and includes related user data for efficient querying.
        """
        logger.info(
            f"Admin {self.request.user.username} (ID: {self.request.user.id}) requested staff requests list"
        )
        return StaffRequest.objects.filter(status="pending").select_related("user")


class StaffRequestDetailView(generics.RetrieveAPIView):
    """
    Handles retrieval of individual staff request details.
    This view provides admin functionality to view detailed information
    about a specific staff request including user data and request history.
    """

    serializer_class = StaffRequestSerializer
    permission_classes = [IsAdminUser]
    queryset = StaffRequest.objects.all()

    def get(self, request, *args, **kwargs):
        """
        Retrieves detailed information about a specific staff request.
        Returns comprehensive staff request data including user information,
        request status, timestamps, and processing details.
        """
        logger.info(
            f"Admin {request.user.username} (ID: {request.user.id}) requested staff request detail for ID: {kwargs.get('pk')}"
        )
        return super().get(request, *args, **kwargs)


class ApproveStaffRequestView(APIView):
    """
    Handles approval of staff registration requests.
    This view provides admin functionality to approve pending staff requests,
    activate user accounts, and grant staff permissions. Only accessible by admin users.
    """

    permission_classes = [IsAdminUser]

    def post(self, request, pk):
        """
        Approves a specific staff registration request.
        Validates admin permissions, finds the staff request, updates its status
        to approved, activates the user account, and grants staff permissions.
        """
        if not request.user.role or request.user.role != "admin":
            logger.error(
                f"Unauthorized access attempt to approve staff request "
                f"by user {request.user.username} (ID: {request.user.id})"
            )
            raise UnauthorizedAccessException("Admin access required.")
        try:
            staff_request = get_object_or_404(StaffRequest, pk=pk, status="pending")
        except NotFoundException:
            logger.error(
                f"Staff request not found for ID: {pk} by admin {request.user.username}"
            )
            raise NotFoundException(UserMessage.STAFF_REQUEST_NOT_FOUND)
        except Exception:
            logger.error(
                f"Unexpected error finding staff request for ID: {pk} by admin {request.user.username}",
                exc_info=True
            )
            raise Exception(GeneralMessage.SOMETHING_WENT_WRONG)

        staff_request.status = "approved"
        staff_request.processed_at = timezone.now()
        staff_request.processed_by = request.user
        staff_request.save()
        user = staff_request.user
        user.is_active = True
        user.role = "station_master"  # Set role to station_master to make is_staff=True
        user.save()
        logger.info(
            f"Admin {request.user.username} (ID: {request.user.id}) approved"
            f"staff request for user {user.username} (ID: {user.id})"
        )
        return Response({"message": f"Staff request for {user.username} approved."})


class RejectStaffRequestView(APIView):
    """
    Handles rejection of staff registration requests.
    This view provides admin functionality to reject pending staff requests
    and deactivate associated user accounts. Only accessible by admin users.
    """

    permission_classes = [IsAdminUser]

    def post(self, request, pk):
        """
        Rejects a specific staff registration request.
        Validates admin permissions, finds the staff request, updates its status
        to rejected, and deactivates the user account.
        """
        try:
            staff_request = get_object_or_404(StaffRequest, pk=pk, status="pending")
        except NotFoundException:
            logger.error(
                f"Staff request not found for ID: {pk} by admin {request.user.username}"
            )
            raise NotFoundException(UserMessage.STAFF_REQUEST_NOT_FOUND)
        except Exception :
            logger.error(
                f"Unexpected error finding staff request for ID: {pk} by admin {request.user.username}",
                exc_info=True
            )
            raise Exception(GeneralMessage.SOMETHING_WENT_WRONG)

        staff_request.status = "rejected"
        staff_request.processed_at = timezone.now()
        staff_request.processed_by = request.user
        staff_request.save()
        user = staff_request.user
        user.is_active = False
        user.save()
        logger.info(
            f"Admin {request.user.username} (ID: {request.user.id})"
            f"rejected staff request for user {user.username} (ID: {user.id})"
        )
        return Response({"detail": f"Staff request for {user.username} rejected."})


class ApproveAllStaffRequestsView(APIView):
    """
    Handles bulk approval of all pending staff requests.

    This view provides admin functionality to approve all pending staff requests
    in a single operation, activating multiple user accounts simultaneously.
    """

    permission_classes = [IsAdminUser]

    def post(self, request):
        """
        Approves all pending staff registration requests.
        Finds all pending staff requests, approves them in bulk, activates
        associated user accounts, and grants staff permissions to all.
        """
        pending_requests = StaffRequest.objects.filter(status="pending")
        approved_count = self._approve_staff_requests(pending_requests, request.user)

        logger.info(
            f"Admin {request.user.username} (ID: {request.user.id})"
            f"approved {approved_count} staff requests"
        )
        return Response(
            {"detail": f"{approved_count} staff requests approved successfully."}
        )

    def _approve_staff_requests(self, pending_requests, admin_user):
        """Approve multiple staff requests"""
        approved_count = 0

        for staff_request in pending_requests:
            self._approve_single_staff_request(staff_request, admin_user)
            approved_count += 1

        return approved_count

    def _approve_single_staff_request(self, staff_request, admin_user):
        """Approve a single staff request"""
        staff_request.status = "approved"
        staff_request.processed_at = timezone.now()
        staff_request.processed_by = admin_user
        staff_request.save()

        user = staff_request.user
        user.is_active = True
        user.role = "station_master"  # Set role to station_master to make is_staff=True
        user.save()


class RejectAllStaffRequestsView(APIView):
    """
    Handles bulk rejection of all pending staff requests.
    This view provides admin functionality to reject all pending staff requests
    in a single operation, deactivating multiple user accounts simultaneously.
    """

    permission_classes = [IsAdminUser]

    def post(self, request):
        """
        Rejects all pending staff registration requests.
        Finds all pending staff requests, rejects them in bulk, and deactivates
        associated user accounts.
        """
        pending_requests = StaffRequest.objects.filter(status="pending")
        rejected_count = self._reject_staff_requests(pending_requests, request.user)

        logger.info(
            f"Admin {request.user.username} (ID: {request.user.id})"
            f"rejected {rejected_count} staff requests"
        )
        return Response({"detail": f"{rejected_count} staff requests rejected."})

    def _reject_staff_requests(self, pending_requests, admin_user):
        """Reject multiple staff requests"""
        rejected_count = 0

        for staff_request in pending_requests:
            self._reject_single_staff_request(staff_request, admin_user)
            rejected_count += 1

        return rejected_count

    def _reject_single_staff_request(self, staff_request, admin_user):
        """Reject a single staff request"""
        staff_request.status = "rejected"
        staff_request.processed_at = timezone.now()
        staff_request.processed_by = admin_user
        staff_request.save()

        user = staff_request.user
        user.is_active = False
        user.save()


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def user_tickets(request):
    """
    Retrieves all ticket bookings for the authenticated user.
    This function provides user access to their booking history and ticket information.
    Only accessible by users with 'user' role, not staff or admin users.
    """
    if getattr(request.user, "role", None) != "user":
        logger.error(
            f"Unauthorized attempt to user tickets by {request.user.username}"
            f"(ID: {request.user.id})role: {getattr(request.user, 'role', 'None')}"
        )
        raise UnauthorizedAccessException(UserMessage.USER_NOT_AUTHORIZED)

    logger.info(
        f"User {request.user.username} (ID: {request.user.id}) requested tickets"
    )
    bookings = Booking.objects.filter(user=request.user).order_by("-created_at")
    serializer = BookingSerializer(bookings, many=True)
    logger.info(
        f"User {request.user.username} (ID: {request.user.id}) retrieved {len(bookings)} tickets"
    )
    return Response(serializer.data)
