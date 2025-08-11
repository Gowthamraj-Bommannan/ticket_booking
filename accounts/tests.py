
# Create your tests here.

from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APITestCase
from rest_framework import status
from django.contrib.auth import get_user_model
from .models import Role, UserOTPVerification, StaffRequest
from django.utils import timezone
from datetime import timedelta
import json

User = get_user_model()


class RoleModelTest(TestCase):
    """Test cases for Role model."""
    
    def setUp(self):
        self.role = Role.objects.create(
            name="test_role",
            description="Test role description"
        )
    
    def test_role_creation(self):
        """Test that role can be created successfully."""
        self.assertEqual(self.role.name, "test_role")
        self.assertEqual(self.role.description, "Test role description")
    
    def test_role_str_representation(self):
        """Test the string representation of role."""
        self.assertEqual(str(self.role), "test_role")


class UserOTPVerificationModelTest(TestCase):
    """Test cases for UserOTPVerification model."""
    
    def setUp(self):
        self.otp = UserOTPVerification.objects.create(
            email="test@example.com",
            otp_code="123456",
            expiry_time=timezone.now() + timedelta(minutes=5),
            attempt_count=0,
            is_verified=False
        )
    
    def test_otp_creation(self):
        """Test that OTP can be created successfully."""
        self.assertEqual(self.otp.email, "test@example.com")
        self.assertEqual(self.otp.otp_code, "123456")
        self.assertFalse(self.otp.is_verified)
    
    def test_otp_str_representation(self):
        """Test the string representation of OTP."""
        self.assertIn("test@example.com", str(self.otp))
        self.assertIn("Pending", str(self.otp))
    
    def test_otp_expiry(self):
        """Test OTP expiry functionality."""
        # Create expired OTP
        expired_otp = UserOTPVerification.objects.create(
            email="expired@example.com",
            otp_code="654321",
            expiry_time=timezone.now() - timedelta(minutes=1),
            attempt_count=0,
            is_verified=False
        )
        
        self.assertTrue(expired_otp.is_expired)
        self.assertFalse(self.otp.is_expired)


class UnifiedRegistrationAPITest(APITestCase):
    """Test cases for unified registration API."""
    
    def setUp(self):
        # Create roles using get_or_create to avoid conflicts with migration signals
        self.user_role, _ = Role.objects.get_or_create(name="user", defaults={"description": "Regular user"})
        self.staff_role, _ = Role.objects.get_or_create(name="station_master", defaults={"description": "Station master"})
        self.admin_role, _ = Role.objects.get_or_create(name="admin", defaults={"description": "Admin"})
    
    def test_user_registration_without_otp(self):
        """Test user registration without OTP (first step)."""
        url = reverse('register-unified')
        data = {
            'username': 'testuser',
            'email': 'test@example.com',
            'mobile_number': '1234567890',
            'password': 'testpass123',
            'confirm_password': 'testpass123',
            'first_name': 'Test',
            'last_name': 'User',
            'role_id': self.user_role.id
        }
        
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED)
        self.assertIn('OTP sent', response.data['message'])
        self.assertIn('otp', response.data)
        
        # Check that OTP record was created
        otp_record = UserOTPVerification.objects.get(email='test@example.com')
        self.assertEqual(otp_record.otp_code, response.data['otp'])
        self.assertFalse(otp_record.is_verified)
    
    def test_user_registration_with_valid_otp(self):
        """Test user registration with valid OTP (second step)."""
        # Create OTP record first
        otp_record = UserOTPVerification.objects.create(
            email='test@example.com',
            otp_code='123456',
            expiry_time=timezone.now() + timedelta(minutes=5),
            attempt_count=0,
            is_verified=False
        )
        
        url = reverse('register-unified')
        data = {
            'username': 'testuser',
            'email': 'test@example.com',
            'mobile_number': '1234567890',
            'password': 'testpass123',
            'confirm_password': 'testpass123',
            'first_name': 'Test',
            'last_name': 'User',
            'role_id': self.user_role.id,
            'otp': '123456'
        }
        
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn('Registration successful', response.data['message'])
        self.assertIn('tokens', response.data)
        self.assertIn('user', response.data)
        
        # Check that user was created
        user = User.objects.get(username='testuser')
        self.assertEqual(user.role, self.user_role)
        self.assertTrue(user.is_active)
        
        # Check that OTP record was deleted after successful verification
        self.assertFalse(UserOTPVerification.objects.filter(email='test@example.com').exists())
    
    def test_staff_registration(self):
        """Test staff registration (should create pending approval)."""
        url = reverse('register-unified')
        data = {
            'username': 'teststaff',
            'email': 'staff@example.com',
            'mobile_number': '9876543210',
            'password': 'staffpass123',
            'confirm_password': 'staffpass123',
            'first_name': 'Test',
            'last_name': 'Staff',
            'role_id': self.staff_role.id
        }
        
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED)
        self.assertIn('OTP sent', response.data['message'])
        
        # Check that OTP record was created
        otp_record = UserOTPVerification.objects.get(email='staff@example.com')
        self.assertEqual(otp_record.otp_code, response.data['otp'])
        self.assertFalse(otp_record.is_verified)
    
    def test_admin_role_registration_forbidden(self):
        """Test that admin role registration is forbidden."""
        url = reverse('register-unified')
        data = {
            'username': 'testadmin',
            'email': 'admin@example.com',
            'mobile_number': '5555555555',
            'password': 'adminpass123',
            'confirm_password': 'adminpass123',
            'first_name': 'Test',
            'last_name': 'Admin',
            'role_id': self.admin_role.id
        }
        
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('Admin role registration is not allowed', str(response.data['error']['role_id']))
    
    def test_invalid_role_id(self):
        """Test registration with invalid role ID."""
        url = reverse('register-unified')
        data = {
            'username': 'testuser',
            'email': 'test@example.com',
            'mobile_number': '1234567890',
            'password': 'testpass123',
            'confirm_password': 'testpass123',
            'role_id': 999  # Non-existent role ID
        }
        
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('Invalid role ID', str(response.data['error']['role_id']))


class OTPValidationAPITest(APITestCase):
    """Test cases for OTP validation API."""
    
    def setUp(self):
        self.otp_record = UserOTPVerification.objects.create(
            email='test@example.com',
            otp_code='123456',
            expiry_time=timezone.now() + timedelta(minutes=5),
            attempt_count=0,
            is_verified=False
        )
    
    def test_valid_otp_validation(self):
        """Test OTP validation with correct OTP."""
        url = reverse('validate-otp')
        data = {
            'email': 'test@example.com',
            'otp_code': '123456'
        }
        
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('OTP validated successfully', response.data['message'])
        
        # Check that OTP was marked as verified
        self.otp_record.refresh_from_db()
        self.assertTrue(self.otp_record.is_verified)
    
    def test_invalid_otp_validation(self):
        """Test OTP validation with incorrect OTP."""
        url = reverse('validate-otp')
        data = {
            'email': 'test@example.com',
            'otp_code': '654321'  # Wrong OTP
        }
        
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('Invalid OTP', response.data['error'])
        
        # Check that attempt count was incremented
        self.otp_record.refresh_from_db()
        self.assertEqual(self.otp_record.attempt_count, 1)
    
    def test_otp_validation_after_3_attempts(self):
        """Test OTP validation after 3 failed attempts."""
        # Set attempt count to 2
        self.otp_record.attempt_count = 2
        self.otp_record.save()
        
        url = reverse('validate-otp')
        data = {
            'email': 'test@example.com',
            'otp_code': '654321'  # Wrong OTP
        }
        
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('Too many failed attempts', response.data['error'])
        
        # Check that OTP record was deleted
        self.assertFalse(UserOTPVerification.objects.filter(email='test@example.com').exists())
    
    def test_expired_otp_validation(self):
        """Test OTP validation with expired OTP."""
        # Create expired OTP
        expired_otp = UserOTPVerification.objects.create(
            email='expired@example.com',
            otp_code='123456',
            expiry_time=timezone.now() - timedelta(minutes=1),
            attempt_count=0,
            is_verified=False
        )
        
        url = reverse('validate-otp')
        data = {
            'email': 'expired@example.com',
            'otp_code': '123456'
        }
        
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        # The expired OTP gets deleted by the signal, so we check for the "No OTP found" message
        self.assertIn('No OTP found', response.data['error'])
        
        # Check that OTP record was deleted
        self.assertFalse(UserOTPVerification.objects.filter(email='expired@example.com').exists())
    
    def test_nonexistent_otp_validation(self):
        """Test OTP validation for non-existent email."""
        url = reverse('validate-otp')
        data = {
            'email': 'nonexistent@example.com',
            'otp_code': '123456'
        }
        
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('No OTP found', response.data['error'])


class StaffApprovalTest(APITestCase):
    """Test cases for staff approval functionality."""
    
    def setUp(self):
        # Create roles using get_or_create to avoid conflicts with migration signals
        self.user_role, _ = Role.objects.get_or_create(name="user", defaults={"description": "Regular user"})
        self.staff_role, _ = Role.objects.get_or_create(name="station_master", defaults={"description": "Station master"})
        self.admin_role, _ = Role.objects.get_or_create(name="admin", defaults={"description": "Admin"})
        
        # Create admin user with correct role (using different username to avoid conflicts)
        self.admin_user = User.objects.create_user(
            username='testadmin',
            email='testadmin@example.com',
            password='adminpass123',
            mobile_number='1111111111',
            role=self.admin_role,
            is_active=True
        )
        
        # Create staff user with pending approval
        self.staff_user = User.objects.create_user(
            username='teststaff',
            email='teststaff@example.com',
            password='staffpass123',
            mobile_number='2222222222',
            role=self.staff_role,
            is_active=False
        )
        
        # Create staff request manually since signal might not work in tests
        self.staff_request, _ = StaffRequest.objects.get_or_create(
            user=self.staff_user,
            defaults={'status': 'pending'}
        )
    
    def test_staff_approval(self):
        """Test staff approval functionality."""
        self.client.force_authenticate(user=self.admin_user)
        
        url = reverse('approve-staff-request', kwargs={'pk': self.staff_request.id})
        response = self.client.post(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('approved successfully', response.data['message'])
        
        # Check that user was activated
        self.staff_user.refresh_from_db()
        self.assertTrue(self.staff_user.is_active)
        
        # Check that staff request was updated
        self.staff_request.refresh_from_db()
        self.assertEqual(self.staff_request.status, 'approved')
        self.assertEqual(self.staff_request.processed_by, self.admin_user)
    
    def test_staff_rejection(self):
        """Test staff rejection functionality."""
        self.client.force_authenticate(user=self.admin_user)
        
        url = reverse('reject-staff-request', kwargs={'pk': self.staff_request.id})
        response = self.client.post(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('rejected successfully', response.data['message'])
        
        # Check that user was deactivated
        self.staff_user.refresh_from_db()
        self.assertFalse(self.staff_user.is_active)
        
        # Check that staff request was updated
        self.staff_request.refresh_from_db()
        self.assertEqual(self.staff_request.status, 'rejected')
        self.assertEqual(self.staff_request.processed_by, self.admin_user)
    
    def test_unauthorized_staff_approval(self):
        """Test staff approval by non-admin user."""
        # Create regular user
        regular_user = User.objects.create_user(
            username='regular',
            email='regular@example.com',
            password='regularpass123',
            mobile_number='3333333333',
            role=self.user_role,
            is_active=True
        )
        
        self.client.force_authenticate(user=regular_user)
        
        url = reverse('approve-staff-request', kwargs={'pk': self.staff_request.id})
        response = self.client.post(url)
        
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class UserModelTest(TestCase):
    """Test cases for updated User model."""
    
    def setUp(self):
        # Create roles using get_or_create to avoid conflicts with migration signals
        self.user_role, _ = Role.objects.get_or_create(name="user", defaults={"description": "Regular user"})
        self.staff_role, _ = Role.objects.get_or_create(name="station_master", defaults={"description": "Station master"})
        self.admin_role, _ = Role.objects.get_or_create(name="admin", defaults={"description": "Admin"})
    
    def test_user_creation_with_role(self):
        """Test user creation with role assignment."""
        user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123',
            mobile_number='1234567890',
            role=self.user_role
        )
        
        self.assertEqual(user.role, self.user_role)
        self.assertEqual(user.role.name, 'user')
    
    def test_user_is_staff_property(self):
        """Test is_staff property based on role."""
        user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123',
            mobile_number='1234567890',
            role=self.user_role
        )
        
        staff_user = User.objects.create_user(
            username='staffuser',
            email='staff@example.com',
            password='staffpass123',
            mobile_number='9876543210',
            role=self.staff_role
        )
        
        admin_user = User.objects.create_user(
            username='adminuser',
            email='admin@example.com',
            password='adminpass123',
            mobile_number='5555555555',
            role=self.admin_role
        )
        
        self.assertFalse(user.is_staff)
        self.assertTrue(staff_user.is_staff)
        self.assertTrue(admin_user.is_staff)
    
    def test_user_is_superuser_property(self):
        """Test is_superuser property based on role."""
        user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123',
            mobile_number='1234567890',
            role=self.user_role
        )
        
        admin_user = User.objects.create_user(
            username='adminuser',
            email='admin@example.com',
            password='adminpass123',
            mobile_number='5555555555',
            role=self.admin_role
        )
        
        self.assertFalse(user.is_superuser)
        self.assertTrue(admin_user.is_superuser)
    
    def test_user_str_representation(self):
        """Test string representation of user."""
        user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123',
            mobile_number='1234567890',
            role=self.user_role
        )
        
        self.assertIn('testuser', str(user))
        self.assertIn('user', str(user))
    
    def test_user_without_role(self):
        """Test user without role assignment."""
        user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123',
            mobile_number='1234567890'
        )
        
        self.assertIsNone(user.role)
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)
        self.assertIn('No Role', str(user))
