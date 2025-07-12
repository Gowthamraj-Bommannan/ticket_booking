from django.shortcuts import render, get_object_or_404
from rest_framework import generics, status, permissions
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView
from django.contrib.auth import get_user_model, update_session_auth_hash
from django.contrib.auth.password_validation import validate_password
from django.utils import timezone
from .serializers import (
    RegisterSerializer, StaffRegisterSerializer, LoginSerializer, UserSerializer, 
    ChangePasswordSerializer, UpdateProfileSerializer, StaffRequestSerializer, StaffRequestApprovalSerializer
)
from .permissions import IsAdminUser
from rest_framework.permissions import IsAuthenticated
from .models import StaffRequest, Role
import logging
from bookingsystem.models import Booking
from bookingsystem.serializers import BookingSerializer
from rest_framework.decorators import api_view, permission_classes
from exceptions.handlers import (
    InvalidCredentialsException, DuplicateEmailException, 
    MobileNumberAlreadyExists, UsernameAlreadyExists,
    InvalidInput, InvalidOTPException, UnauthorizedAccessException,
    UserNotFoundException
)
from utils.constants import UserMessage, AlreadyExistsMessage

User = get_user_model()
logger = logging.getLogger("accounts")

def send_otp(mobile_number, email):
    """
    Sends OTP to the provided mobile number and email address.
    
    This is a mock implementation that simulates OTP sending functionality.
    In production, this should integrate with actual SMS/email gateways.
    
    Args:
        mobile_number (str): The mobile number to send OTP to
        email (str): The email address to send OTP to
        
    Returns:
        str: The OTP code (always returns '123456' for demo purposes)
    """
    # In production, integrate with SMS/email gateway
    logger.debug(f"OTP sent to mobile: {mobile_number} and email: {email}")
    return '123456'  # Always returns 123456 for demo

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
        
        Handles both initial registration (sends OTP) and final registration (verifies OTP).
        Creates user account with 'user' role upon successful OTP verification.
        
        Args:
            request: HTTP request object containing registration data
            
        Returns:
            Response: Success response with tokens and user data, or OTP sent confirmation
        """
        serializer = RegisterSerializer(data=request.data)
        try:
            serializer.is_valid(raise_exception=True)
            return self._handle_registration_request(request, serializer)
        except Exception as e:
            return self._handle_registration_error(e, serializer)
    
    def _handle_registration_request(self, request, serializer):
        """Handle the registration request logic"""
        mobile_number = serializer.validated_data['mobile_number']
        email = serializer.validated_data['email']
        username = serializer.validated_data['username']
        otp = request.data.get('otp')
        
        if not otp:
            return self._send_otp_response(mobile_number, email)
        
        if otp != '123456':
            logger.warning(f"Invalid OTP provided for registration - Email: {email}, Username: {username}")
            raise InvalidOTPException()
        
        return self._complete_registration(serializer)
    
    def _send_otp_response(self, mobile_number, email):
        """Send OTP and return response"""
        send_otp(mobile_number, email)
        logger.info(f"OTP sent for registration - Email: {email}, Mobile: {mobile_number}")
        return Response({
            'detail': UserMessage.OTP_SENT_REGISTRATION,
                    'otp': '123456'
                }, status=202)
    
    def _complete_registration(self, serializer):
        """Complete the registration process"""
        # Create user with business logic moved from serializer
        validated_data = serializer.validated_data
        user = User.objects.create_user(
            username=validated_data['username'],
            email=validated_data['email'],
            mobile_number=validated_data['mobile_number'],
            password=validated_data['password'],
            first_name=validated_data.get('first_name', ''),
            last_name=validated_data.get('last_name', ''),
            role='user',  # Always set role to user for regular registration
        )
        logger.info(f"User created successfully - Username: {user.username}, Email: {user.email}")
        
        refresh = RefreshToken.for_user(user)
        data = {
                'refresh': str(refresh),
                'access': str(refresh.access_token),
                'user': UserSerializer(user).data
            }
        logger.info(f"User {user.username} (ID: {user.id}) registered successfully")
        return Response(data, status=201)
    
    def _handle_registration_error(self, e, serializer):
        """Handle registration errors"""
        # Re-raise custom exceptions as they are
        if isinstance(e, (DuplicateEmailException, MobileNumberAlreadyExists, UsernameAlreadyExists, InvalidOTPException)):
            logger.warning(f"Registration failed - {type(e).__name__}: {str(e)}")
            raise
        # Handle other validation errors
        logger.error(f"Unexpected error during registration: {str(e)}", exc_info=True)
        raise InvalidInput(serializer.errors)

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
        
        Handles both initial registration (sends OTP) and final registration (verifies OTP).
        Creates staff user account with 'station_master' role and creates approval request.
        
        Args:
            request: HTTP request object containing staff registration data
            
        Returns:
            Response: Success response with approval status, or OTP sent confirmation
        """
        serializer = StaffRegisterSerializer(data=request.data)
        try:
            serializer.is_valid(raise_exception=True)
            return self._handle_staff_registration_request(request, serializer)
        except Exception as e:
            return self._handle_staff_registration_error(e, serializer)
    
    def _handle_staff_registration_request(self, request, serializer):
        """Handle the staff registration request logic"""
        mobile_number = serializer.validated_data['mobile_number']
        email = serializer.validated_data['email']
        username = serializer.validated_data['username']
        otp = request.data.get('otp')
        
        if not otp:
            return self._send_staff_otp_response(mobile_number, email)
        
        if otp != '123456':
            logger.warning(f"Invalid OTP provided for staff registration - Email: {email}, Username: {username}")
            raise InvalidOTPException()
        
        return self._complete_staff_registration(serializer)
    
    def _send_staff_otp_response(self, mobile_number, email):
        """Send OTP for staff registration and return response"""
        send_otp(mobile_number, email)
        logger.info(f"OTP sent for staff registration - Email: {email}, Mobile: {mobile_number}")
        return Response({
            'detail': UserMessage.OTP_SENT_STAFF_REGISTRATION,
                    'otp': '123456'
                }, status=202)
    
    def _complete_staff_registration(self, serializer):
        """Complete the staff registration process"""
        # Create staff user with business logic moved from serializer
        validated_data = serializer.validated_data
        user = User.objects.create_user(
            username=validated_data['username'],
            email=validated_data['email'],
            mobile_number=validated_data['mobile_number'],
            password=validated_data['password'],
            first_name=validated_data.get('first_name', ''),
            last_name=validated_data.get('last_name', ''),
            role='station_master',  # Set role to station_master
            is_active=False,  # Initially inactive until approved
        )
        logger.info(f"Staff user created successfully - Username: {user.username}, Email: {user.email}")
        StaffRequest.objects.get_or_create(user=user)
        logger.info(f"Staff user {user.username} (ID: {user.id}) registered successfully, waiting for approval")
        return Response({
            'detail': UserMessage.STAFF_REGISTRATION_WAITING,
                'user': UserSerializer(user).data
            }, status=201)
    
    def _handle_staff_registration_error(self, e, serializer):
        """Handle staff registration errors"""
        # Re-raise custom exceptions as they are
        if isinstance(e, (DuplicateEmailException, MobileNumberAlreadyExists, UsernameAlreadyExists, InvalidOTPException)):
            logger.warning(f"Staff registration failed - {type(e).__name__}: {str(e)}")
            raise
        # Handle other validation errors
        logger.error(f"Unexpected error during staff registration: {str(e)}", exc_info=True)
        raise InvalidInput(serializer.errors)

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
            user = serializer.validated_data['user']
            user.last_login = timezone.localtime(timezone.now())
            user.save(update_fields=['last_login'])
            refresh = RefreshToken.for_user(user)
            data = {
                'refresh': str(refresh),
                'access': str(refresh.access_token),
                'user': UserSerializer(user).data
            }
            logger.info(f"User {user.username} (ID: {user.id}) logged in successfully")
            return Response(data)
        except Exception as e:
            # Re-raise custom exceptions as they are
            if isinstance(e, (InvalidCredentialsException, InvalidInput)):
                logger.warning(f"Login failed - {type(e).__name__}: {str(e)}")
                raise
            # Handle other validation errors
            logger.error(f"Unexpected error during login: {str(e)}", exc_info=True)
            raise InvalidInput(serializer.errors)

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
        # JWT logout is client-side (just delete token), but you can blacklist if needed
        logger.info(f"User {request.user.username} (ID: {request.user.id}) logged out")
        return Response({'detail': 'Logged out successfully.'}, status=200)

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
        logger.debug(f"User {request.user.username} (ID: {request.user.id}) requested profile")
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
        serializer = UpdateProfileSerializer(self.request.user, data=request.data, partial=True, context={'request': request})
        try:
            serializer.is_valid(raise_exception=True)
            serializer.save()
            logger.info(f"User {request.user.username} (ID: {request.user.id}) updated profile successfully")
            return Response(UserSerializer(self.request.user).data)
        except Exception as e:
            # Re-raise custom exceptions as they are
            if isinstance(e, (DuplicateEmailException, MobileNumberAlreadyExists)):
                logger.warning(f"Profile update failed for user {request.user.username} - {type(e).__name__}: {str(e)}")
                raise
            # Handle other validation errors
            logger.error(f"Unexpected error during profile update for user {request.user.username}: {str(e)}", exc_info=True)
            raise InvalidInput(serializer.errors)

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
            if not user.check_password(serializer.validated_data['old_password']):
                logger.warning(f"Password change failed for user {user.username} - Wrong old password")
                raise InvalidCredentialsException('Wrong password.')
            try:
                validate_password(serializer.validated_data['new_password'], user)
            except Exception as e:
                logger.warning(f"Password validation failed for user {user.username}: {str(e)}")
                raise InvalidInput(e.messages)
            user.set_password(serializer.validated_data['new_password'])
            user.save()
            update_session_auth_hash(request, user)
            logger.info(f"User {user.username} (ID: {user.id}) changed password successfully")
            return Response({'detail': UserMessage.PASSWORD_CHANGED_SUCCESS})
        except Exception as e:
            # Re-raise custom exceptions as they are
            if isinstance(e, (InvalidCredentialsException, InvalidInput)):
                raise
            # Handle other validation errors
            logger.error(f"Unexpected error during password change for user {request.user.username}: {str(e)}", exc_info=True)
            raise InvalidInput(serializer.errors)

class BookingHistoryView(APIView):
    """
    Handles user booking history retrieval.
    
    This view provides access to user's booking history and related information.
    Currently serves as a placeholder for future booking history implementation.
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request):
        """
        Retrieves user's booking history.
        
        Currently returns placeholder data. To be implemented with actual
        booking history retrieval logic.
        
        Args:
            request: HTTP request object
            
        Returns:
            Response: Placeholder booking history data
        """
        # Placeholder: Replace with actual booking history logic
        logger.debug(f"User {request.user.username} (ID: {request.user.id}) requested booking history")
        return Response({'history': []})

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
        
        Returns:
            QuerySet: Filtered staff requests with pending status
        """
        logger.debug(f"Admin {self.request.user.username} (ID: {self.request.user.id}) requested staff requests list")
        return StaffRequest.objects.filter(status='pending').select_related('user')

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
        
        Args:
            request: HTTP request object
            *args: Additional positional arguments
            **kwargs: Additional keyword arguments containing request ID
            
        Returns:
            Response: Detailed staff request information
        """
        logger.debug(f"Admin {request.user.username} (ID: {request.user.id}) requested staff request detail for ID: {kwargs.get('pk')}")
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
        
        Args:
            request: HTTP request object
            pk: Primary key of the staff request to approve
            
        Returns:
            Response: Success confirmation message
        """
        if not request.user.role or request.user.role != 'admin':
            logger.warning(f"Unauthorized access attempt to approve staff request by user {request.user.username} (ID: {request.user.id})")
            raise UnauthorizedAccessException('Admin access required.')
        try:
            staff_request = get_object_or_404(StaffRequest, pk=pk, status='pending')
        except:
            logger.warning(f"Staff request not found for ID: {pk} by admin {request.user.username}")
            raise UserNotFoundException('Staff request not found.')
        
        staff_request.status = 'approved'
        staff_request.processed_at = timezone.now()
        staff_request.processed_by = request.user
        staff_request.save()
        user = staff_request.user
        user.is_active = True
        user.role = 'station_master'  # Set role to station_master to make is_staff=True
        user.save()
        logger.info(f"Admin {request.user.username} (ID: {request.user.id}) approved staff request for user {user.username} (ID: {user.id})")
        return Response({'message': f'Staff request for {user.username} approved.'})

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
        
        Args:
            request: HTTP request object
            pk: Primary key of the staff request to reject
            
        Returns:
            Response: Success confirmation message
        """
        try:
            staff_request = get_object_or_404(StaffRequest, pk=pk, status='pending')
        except:
            logger.warning(f"Staff request not found for ID: {pk} by admin {request.user.username}")
            raise UserNotFoundException('Staff request not found.')
        
        staff_request.status = 'rejected'
        staff_request.processed_at = timezone.now()
        staff_request.processed_by = request.user
        staff_request.save()
        user = staff_request.user
        user.is_active = False
        user.save()
        logger.info(f"Admin {request.user.username} (ID: {request.user.id}) rejected staff request for user {user.username} (ID: {user.id})")
        return Response({'detail': f'Staff request for {user.username} rejected.'})

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
        
        Args:
            request: HTTP request object
            
        Returns:
            Response: Success confirmation with count of approved requests
        """
        pending_requests = StaffRequest.objects.filter(status='pending')
        approved_count = self._approve_staff_requests(pending_requests, request.user)
        
        logger.info(f"Admin {request.user.username} (ID: {request.user.id}) approved {approved_count} staff requests")
        return Response({
            'detail': f'{approved_count} staff requests approved successfully.'
        })
    
    def _approve_staff_requests(self, pending_requests, admin_user):
        """Approve multiple staff requests"""
        approved_count = 0
        
        for staff_request in pending_requests:
            self._approve_single_staff_request(staff_request, admin_user)
            approved_count += 1
        
        return approved_count
    
    def _approve_single_staff_request(self, staff_request, admin_user):
        """Approve a single staff request"""
        staff_request.status = 'approved'
        staff_request.processed_at = timezone.now()
        staff_request.processed_by = admin_user
        staff_request.save()
        
        user = staff_request.user
        user.is_active = True
        user.role = 'station_master'  # Set role to station_master to make is_staff=True
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
        
        Args:
            request: HTTP request object
            
        Returns:
            Response: Success confirmation with count of rejected requests
        """
        pending_requests = StaffRequest.objects.filter(status='pending')
        rejected_count = self._reject_staff_requests(pending_requests, request.user)
        
        logger.info(f"Admin {request.user.username} (ID: {request.user.id}) rejected {rejected_count} staff requests")
        return Response({
            'detail': f'{rejected_count} staff requests rejected.'
        })
    
    def _reject_staff_requests(self, pending_requests, admin_user):
        """Reject multiple staff requests"""
        rejected_count = 0
        
        for staff_request in pending_requests:
            self._reject_single_staff_request(staff_request, admin_user)
            rejected_count += 1
        
        return rejected_count
    
    def _reject_single_staff_request(self, staff_request, admin_user):
        """Reject a single staff request"""
        staff_request.status = 'rejected'
        staff_request.processed_at = timezone.now()
        staff_request.processed_by = admin_user
        staff_request.save()
        
        user = staff_request.user
        user.is_active = False
        user.save()

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def user_tickets(request):
    """
    Retrieves all ticket bookings for the authenticated user.
    
    This function provides user access to their booking history and ticket information.
    Only accessible by users with 'user' role, not staff or admin users.
    
    Args:
        request: HTTP request object
        
    Returns:
        Response: Serialized list of user's booking data
    """
    if getattr(request.user, 'role', None) != 'user':
        logger.warning(f"Unauthorized access attempt to user tickets by {request.user.username} (ID: {request.user.id}) with role: {getattr(request.user, 'role', 'None')}")
        raise UnauthorizedAccessException(UserMessage.USER_NOT_AUTHORIZED)
    
    logger.debug(f"User {request.user.username} (ID: {request.user.id}) requested tickets")
    bookings = Booking.objects.filter(user=request.user).order_by('-created_at')
    serializer = BookingSerializer(bookings, many=True)
    logger.info(f"User {request.user.username} (ID: {request.user.id}) retrieved {len(bookings)} tickets")
    return Response(serializer.data)
