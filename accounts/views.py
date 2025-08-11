from rest_framework import generics, permissions
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView
from django.contrib.auth import get_user_model, update_session_auth_hash
from django.utils import timezone
from .serializers import (
    LoginSerializer,
    UserSerializer,
    ChangePasswordSerializer,
    UpdateProfileSerializer,
    StaffRequestSerializer,
    RegistrationSerializer,
    OTPValidationSerializer,
)
from rest_framework.permissions import IsAuthenticated
from .models import StaffRequest, Role
import logging
from utils.permission_helpers import IsAdminUser
from bookingsystem.models import Booking
from bookingsystem.serializers import BookingSerializer
from rest_framework.decorators import api_view, permission_classes
from exceptions.handlers import (
    InvalidInputException,
    TimeoutException,
    PermissionDeniedException,
)
from utils.constants import (UserMessage, GeneralMessage)
from utils.registration_helpers import (
    OTPHelper,
    UserCreationHelper,
    StaffRequestHelper,
)

User = get_user_model()
logger = logging.getLogger("accounts")


class UnifiedRegistrationView(APIView):
    """
    Unified registration view that handles both user and staff registration.
    
    This view manages the complete registration process including:
    - Role-based registration logic
    - OTP generation and verification for users
    - Pending approval workflow for staff
    - User account creation with appropriate role assignment
    """
    
    permission_classes = [permissions.AllowAny]
    
    def post(self, request):
        """
        Processes unified registration requests.
        
        Handles registration based on role_id:
        - If role is "user": Send OTP and wait for verification
        - If role is "station_master": Create pending approval request
        
        Args:
            request: HTTP request object containing registration data
            
        Returns:
            Response: Success response with appropriate message based on role
        """
        serializer = RegistrationSerializer(data=request.data)
        if not serializer.is_valid():
            raise InvalidInputException(serializer.errors)
            
        validated_data = serializer.validated_data
        
        # Get the role
        role_id = validated_data.pop('role_id')
        role = Role.objects.get(id=role_id)
        
        if role.name == "user":
            return self._handle_user_registration(validated_data, role)
        elif role.name == "station_master":
            return self._handle_staff_registration(validated_data, role)
        else:
            raise InvalidInputException("Invalid role for registration.")
    
    def _handle_user_registration(self, validated_data, role):
        """
        Handle user registration with OTP verification.
        """
        # Check if OTP is provided
        otp_code = self.request.data.get('otp')
        
        if not otp_code:
            # First step: Generate and send OTP
            return OTPHelper.generate_and_send_otp(validated_data["email"], validated_data, role)
        else:
            # Second step: Verify OTP and create user
            return self._verify_otp_and_create_user(validated_data, role, otp_code)
    
    def _handle_staff_registration(self, validated_data, role):
        """
        Handle staff registration with OTP verification.
        """
        # Check if OTP is provided
        otp_code = self.request.data.get('otp')
        
        if not otp_code:
            # First step: Generate and send OTP
            return OTPHelper.generate_and_send_otp(validated_data["email"], validated_data, role)
        else:
            # Second step: Verify OTP and create staff user
            return self._verify_otp_and_create_staff_user(validated_data, role, otp_code)
    
    def _verify_otp_and_create_user(self, validated_data, role, otp_code):
        """
        Verify OTP and create user account.
        """
        email = validated_data["email"]
        
        # Validate OTP using utility function
        otp_record = OTPHelper.validate_otp_and_get_record(email, otp_code)
        
        # Create user using utility function
        user = UserCreationHelper.create_user_with_role(validated_data, role, is_active=True)
        
        # Cleanup OTP record
        OTPHelper.cleanup_otp_record(otp_record)
        
        # Return standardized response
        return UserCreationHelper.create_user_registration_response(user)
    
    def _verify_otp_and_create_staff_user(self, validated_data, role, otp_code):
        """
        Verify OTP and create staff user account with pending approval.
        """
        email = validated_data["email"]
        
        # Validate OTP using utility function
        otp_record = OTPHelper.validate_otp_and_get_record(email, otp_code)
        
        # Create staff user using utility function
        user = UserCreationHelper.create_user_with_role(validated_data, role, is_active=False)
        
        # Cleanup OTP record
        OTPHelper.cleanup_otp_record(otp_record)
        
        # Return standardized staff response
        return UserCreationHelper.create_staff_registration_response(user)


class OTPValidationView(APIView):
    """
    Dedicated OTP validation endpoint.
    
    This view handles OTP validation for user registration including:
    - OTP verification against stored records
    - Attempt tracking and failure handling
    - User account creation upon successful verification
    """
    
    permission_classes = [permissions.AllowAny]
    
    def post(self, request):
        """
        Validates OTP and completes user registration.
        
        Args:
            request: HTTP request object containing registration data and otp_code
            
        Returns:
            Response: Success or error response based on OTP validation
        """
        try:
            # Check if this is a complete registration request
            if 'username' in request.data and 'password' in request.data:
                # This is a complete registration with OTP
                return self._handle_complete_registration(request)
            else:
                # This is just OTP validation
                return self._handle_otp_validation_only(request)
            
        except (InvalidInputException, TimeoutException) as e:
            raise e
        except Exception as e:
            logger.error(f"Unexpected error during OTP validation: {str(e)}", exc_info=True)
            raise InvalidInputException(GeneralMessage.SOMETHING_WENT_WRONG)
    
    def _handle_complete_registration(self, request):
        """
        Handle complete registration with OTP verification and user creation.
        """
        # Validate registration data
        registration_serializer = UnifiedRegistrationSerializer(data=request.data)
        if not registration_serializer.is_valid():
            return Response(registration_serializer.errors, status=400)
        
        validated_data = registration_serializer.validated_data
        role_id = validated_data.pop('role_id')
        role = Role.objects.get(id=role_id)
        
        # Check if admin role registration is forbidden
        if role.name == "admin":
            raise InvalidInputException(UserMessage.ADMIN_ROLE_REGISTRATION_NOT_ALLOWED)
        
        # Validate OTP
        email = validated_data["email"]
        otp_code = request.data.get('otp')
        
        if not otp_code:
            raise InvalidInputException("OTP is required for registration.")
        
        # Validate OTP using utility function
        otp_record = OTPHelper.validate_otp_and_get_record(email, otp_code)
        
        # Create user based on role
        if role.name == "user":
            user = UserCreationHelper.create_user_with_role(validated_data, role, is_active=True)
            OTPHelper.cleanup_otp_record(otp_record)
            return UserCreationHelper.create_user_registration_response(user)
            
        elif role.name == "station_master":
            user = UserCreationHelper.create_user_with_role(validated_data, role, is_active=False)
            OTPHelper.cleanup_otp_record(otp_record)
            return UserCreationHelper.create_staff_registration_response(user)
    
    def _handle_otp_validation_only(self, request):
        """
        Handle OTP validation only (without user creation).
        """
        serializer = OTPValidationSerializer(data=request.data)
        
        if not serializer.is_valid():
            raise InvalidInputException(str(serializer.errors))
        
        email = serializer.validated_data['email']
        otp_code = serializer.validated_data['otp_code']
        
        # Validate OTP using utility function
        otp_record = OTPHelper.validate_otp_and_get_record(email, otp_code)
        
        # Mark OTP as verified (but don't delete for validation-only)
        otp_record.is_verified = True
        otp_record.save()
        
        return Response({
            "message": "OTP validated successfully.",
            "email": email
        }, status=200)


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

        Authenticates user credentials and returns JWT tokens with user data.
        Updates last login timestamp for successful logins.

        Args:
            request: HTTP request object containing login credentials

        Returns:
            Response: JWT tokens and user data for successful authentication
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = serializer.validated_data["user"]
        user.last_login = timezone.now()
        user.save()

        refresh = RefreshToken.for_user(user)
        return Response({
            "tokens": {
                "refresh": str(refresh),
                "access": str(refresh.access_token),
            },
            "user": UserSerializer(user).data,
        })


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

        Provides logout confirmation for client-side token cleanup.
        No server-side token invalidation is performed.

        Args:
            request: HTTP request object

        Returns:
            Response: Logout confirmation message
        """
        return Response({"detail": "Successfully logged out."})


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
        Returns the current user object.
        """
        return self.request.user

    def get(self, request, *args, **kwargs):
        """
        Retrieves current user's profile information.

        Returns comprehensive user profile data including:
        - Basic profile fields (username, email, mobile_number, names)
        - System fields (role, timestamps, active status)
        - Role information with nested serializer

        Args:
            request: HTTP request object

        Returns:
            Response: User profile data
        """
        serializer = self.get_serializer(self.get_object())
        return Response(serializer.data)

    def put(self, request, *args, **kwargs):
        """
        Updates current user's profile information.

        Handles profile updates with validation for:
        - Email and mobile number uniqueness
        - Field format validation
        - Partial updates support

        Args:
            request: HTTP request object containing updated profile data

        Returns:
            Response: Updated user profile data
        """
        user = self.get_object()
        serializer = UpdateProfileSerializer(
            user, data=request.data, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(UserSerializer(user).data)


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

        Validates current password and updates to new password.
        Maintains session authentication hash for security.

        Args:
            request: HTTP request object containing old and new passwords

        Returns:
            Response: Success or error message
        """
        serializer = ChangePasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = request.user
        old_password = serializer.validated_data["old_password"]
        new_password = serializer.validated_data["new_password"]

        if not user.check_password(old_password):
            raise InvalidInputException("Current password is incorrect.")

        user.set_password(new_password)
        user.save()
        update_session_auth_hash(request, user)

        return Response({"message": UserMessage.PASSWORD_CHANGED_SUCCESS})


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
        Returns filtered queryset of staff requests.
        """
        return StaffRequest.objects.select_related("user").all()


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
        Retrieves detailed staff request information.

        Returns comprehensive staff request data including:
        - Request details (status, timestamps, notes)
        - Associated user information
        - Processing history

        Args:
            request: HTTP request object

        Returns:
            Response: Staff request details
        """
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
        Approves a specific staff request.

        Updates staff request status to approved and activates user account.
        Grants staff permissions to the approved user.

        Args:
            request: HTTP request object
            pk: Primary key of the staff request to approve

        Returns:
            Response: Success or error message
        """
        staff_request = StaffRequestHelper.get_staff_request_or_404(pk)
        StaffRequestHelper.validate_staff_request_status(staff_request)
        StaffRequestHelper.approve_staff_request(staff_request, request.user)

        return Response({"message": "Staff request approved successfully."})


class RejectStaffRequestView(APIView):
    """
    Handles rejection of staff registration requests.
    This view provides admin functionality to reject pending staff requests
    and deactivate associated user accounts. Only accessible by admin users.
    """

    permission_classes = [IsAdminUser]

    def post(self, request, pk):
        """
        Rejects a specific staff request.

        Updates staff request status to rejected and deactivates user account.
        Removes staff permissions from the rejected user.

        Args:
            request: HTTP request object
            pk: Primary key of the staff request to reject

        Returns:
            Response: Success or error message
        """
        staff_request = StaffRequestHelper.get_staff_request_or_404(pk)
        StaffRequestHelper.validate_staff_request_status(staff_request)
        StaffRequestHelper.reject_staff_request(staff_request, request.user)

        return Response({"message": "Staff request rejected successfully."})


class ApproveAllStaffRequestsView(APIView):
    """
    Handles bulk approval of all pending staff requests.

    This view provides admin functionality to approve all pending staff requests
    in a single operation, activating multiple user accounts simultaneously.
    """

    permission_classes = [IsAdminUser]

    def post(self, request):
        """
        Approves all pending staff requests.

        Processes all pending staff requests in bulk, updating their status
        to approved and activating associated user accounts.

        Args:
            request: HTTP request object

        Returns:
            Response: Success message with count of approved requests
        """
        pending_requests = StaffRequest.objects.filter(status="pending")
        approved_count = pending_requests.count()

        if approved_count == 0:
            return Response({"message": "No pending staff requests to approve."})

        self._approve_staff_requests(pending_requests, request.user)

        return Response({
            "message": f"Successfully approved {approved_count} staff requests."
        })

    def _approve_staff_requests(self, pending_requests, admin_user):
        """
        Approves multiple staff requests in bulk.
        """
        for staff_request in pending_requests:
            self._approve_single_staff_request(staff_request, admin_user)

    def _approve_single_staff_request(self, staff_request, admin_user):
        """
        Approves a single staff request.
        """
        StaffRequestHelper.approve_staff_request(staff_request, admin_user)
    
    def _reject_single_staff_request(self, staff_request, admin_user):
        """
        Rejects a single staff request.
        """
        StaffRequestHelper.reject_staff_request(staff_request, admin_user)


class RejectAllStaffRequestsView(APIView):
    """
    Handles bulk rejection of all pending staff requests.

    This view provides admin functionality to reject all pending staff requests
    in a single operation, deactivating multiple user accounts simultaneously.
    """

    permission_classes = [IsAdminUser]

    def post(self, request):
        """
        Rejects all pending staff requests.

        Processes all pending staff requests in bulk, updating their status
        to rejected and deactivating associated user accounts.

        Args:
            request: HTTP request object

        Returns:
            Response: Success message with count of rejected requests
        """
        pending_requests = StaffRequest.objects.filter(status="pending")
        rejected_count = pending_requests.count()

        if rejected_count == 0:
            return Response({"message": "No pending staff requests to reject."})

        self._reject_staff_requests(pending_requests, request.user)

        return Response({
            "message": f"Successfully rejected {rejected_count} staff requests."
        })

    def _reject_staff_requests(self, pending_requests, admin_user):
        """
        Rejects multiple staff requests in bulk.
        """
        for staff_request in pending_requests:
            self._reject_single_staff_request(staff_request, admin_user)

    def _reject_single_staff_request(self, staff_request, admin_user):
        """
        Rejects a single staff request.
        """
        staff_request.status = "rejected"
        staff_request.processed_at = timezone.now()
        staff_request.processed_by = admin_user
        staff_request.save()


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def user_tickets(request):
    """
    Retrieves tickets booked by the current user.

    This view provides user-specific ticket information including:
    - All bookings made by the authenticated user
    - Booking details with train and station information
    - Payment status and booking history

    Only accessible by authenticated users to view their own tickets.

    Args:
        request: HTTP request object

    Returns:
        Response: List of user's booking data
    """
    if request.user.role and request.user.role.name == "admin":
        raise PermissionDeniedException(UserMessage.ADMIN_CANNOT_CREATE_BOOKING)

    bookings = Booking.objects.filter(user=request.user).select_related(
        "train", "from_station", "to_station"
    )
    serializer = BookingSerializer(bookings, many=True)

    return Response(serializer.data)
