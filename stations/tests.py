from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from django.urls import reverse
from .models import Station
from routes.models import RouteEdge
import json

User = get_user_model()


class StationModelTest(TestCase):
    """Test cases for Station model validation and behavior"""

    def setUp(self):
        """Set up test data"""
        self.admin_user = User.objects.create_user(
            username="admin_user",
            email="admin@test.com",
            password="adminpass123",
            role="admin",
            is_active=True
        )
        
        self.station_master = User.objects.create_user(
            username="station_master1",
            email="master1@test.com",
            password="masterpass123",
            role="station_master",
            is_active=True
        )

    def test_station_creation_valid_data(self):
        """Test creating station with valid data"""
        station = Station.objects.create(
            name="Central Station",
            code="CST",
            city="Mumbai",
            state="Maharashtra"
        )
        self.assertEqual(station.name, "Central Station")
        self.assertEqual(station.code, "CST")
        self.assertTrue(station.is_active)
        self.assertIsNone(station.station_master)

    def test_station_code_uppercase_conversion(self):
        """Test that station code is automatically converted to uppercase"""
        station = Station.objects.create(
            name="Test Station",
            code="test",
            city="Test City",
            state="Test State"
        )
        self.assertEqual(station.code, "TEST")

    def test_station_with_station_master(self):
        """Test creating station with assigned station master"""
        station = Station.objects.create(
            name="Manned Station",
            code="MS1",
            city="Test City",
            state="Test State",
            station_master=self.station_master
        )
        self.assertEqual(station.station_master, self.station_master)

    def test_station_soft_delete(self):
        """Test soft delete functionality"""
        station = Station.objects.create(
            name="To Delete",
            code="DEL",
            city="Test City",
            state="Test State"
        )
        station.is_active = False
        station.save()
        
        # Should not appear in default queryset
        self.assertNotIn(station, Station.objects.all())
        # Should appear in all_objects
        self.assertIn(station, Station.all_objects.all())

    def test_station_string_representation(self):
        """Test string representation of station"""
        station = Station.objects.create(
            name="Test Station",
            code="TST",
            city="Test City",
            state="Test State"
        )
        self.assertEqual(str(station), "Test Station (TST)")
        
        # Test inactive station
        station.is_active = False
        station.save()
        self.assertEqual(str(station), "Test Station (TST) (Inactive)")

    def test_station_validation_code_too_short(self):
        """Test validation error for station code too short"""
        with self.assertRaises(Exception):
            Station.objects.create(
                name="Test Station",
                code="A",  # Too short
                city="Test City",
                state="Test State"
            )

    def test_station_validation_code_too_long(self):
        """Test validation error for station code too long"""
        with self.assertRaises(Exception):
            Station.objects.create(
                name="Test Station",
                code="ABCDEF",  # Too long
                city="Test City",
                state="Test State"
            )

    def test_station_validation_name_too_short(self):
        """Test validation error for station name too short"""
        with self.assertRaises(Exception):
            Station.objects.create(
                name="AB",  # Too short
                code="TST",
                city="Test City",
                state="Test State"
            )

    def test_station_validation_duplicate_code(self):
        """Test validation error for duplicate station code"""
        Station.objects.create(
            name="First Station",
            code="TST",
            city="Test City",
            state="Test State"
        )
        
        with self.assertRaises(Exception):
            Station.objects.create(
                name="Second Station",
                code="TST",  # Duplicate code
                city="Test City",
                state="Test State"
            )

    def test_station_validation_duplicate_name(self):
        """Test validation error for duplicate station name"""
        Station.objects.create(
            name="Test Station",
            code="TST1",
            city="Test City",
            state="Test State"
        )
        
        with self.assertRaises(Exception):
            Station.objects.create(
                name="Test Station",  # Duplicate name
                code="TST2",
                city="Test City",
                state="Test State"
            )


class StationAPITest(APITestCase):
    """Test cases for Station API endpoints"""

    def setUp(self):
        """Set up test data"""
        self.client = APIClient()
        
        # Create admin user
        self.admin_user = User.objects.create_user(
            username="admin_user",
            email="admin@test.com",
            password="adminpass123",
            role="admin",
            is_active=True
        )
        
        # Create station master
        self.station_master = User.objects.create_user(
            username="station_master1",
            email="master1@test.com",
            password="masterpass123",
            role="station_master",
            is_active=True
        )
        
        # Create regular user
        self.regular_user = User.objects.create_user(
            username="regular_user",
            email="user@test.com",
            password="userpass123",
            role="user",
            is_active=True
        )
        
        # Create test stations
        self.station1 = Station.objects.create(
            name="Central Station",
            code="CST",
            city="Mumbai",
            state="Maharashtra"
        )
        
        self.station2 = Station.objects.create(
            name="Delhi Junction",
            code="DLJ",
            city="Delhi",
            state="Delhi"
        )

    def test_list_stations_authenticated_user(self):
        """Test listing stations for authenticated user"""
        self.client.force_authenticate(user=self.regular_user)
        url = reverse('admin-stations-list')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)

    def test_list_stations_unauthenticated_user(self):
        """Test listing stations for unauthenticated user"""
        url = reverse('admin-stations-list')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_create_station_admin_user(self):
        """Test creating station with admin user"""
        self.client.force_authenticate(user=self.admin_user)
        url = reverse('admin-stations-list')
        data = {
            "name": "New Station",
            "code": "NST",
            "city": "New City",
            "state": "New State"
        }
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Station.objects.count(), 3)

    def test_create_station_regular_user_forbidden(self):
        """Test creating station with regular user (should be forbidden)"""
        self.client.force_authenticate(user=self.regular_user)
        url = reverse('admin-stations-list')
        data = {
            "name": "New Station",
            "code": "NST",
            "city": "New City",
            "state": "New State"
        }
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_create_station_invalid_data(self):
        """Test creating station with invalid data"""
        self.client.force_authenticate(user=self.admin_user)
        url = reverse('admin-stations-list')
        data = {
            "name": "AB",  # Too short
            "code": "A",    # Too short
            "city": "Test City",
            "state": "Test State"
        }
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_station_duplicate_code(self):
        """Test creating station with duplicate code"""
        self.client.force_authenticate(user=self.admin_user)
        url = reverse('admin-stations-list')
        data = {
            "name": "Another Station",
            "code": "CST",  # Duplicate code
            "city": "Test City",
            "state": "Test State"
        }
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_retrieve_station_valid_code(self):
        """Test retrieving station with valid code"""
        self.client.force_authenticate(user=self.regular_user)
        url = reverse('admin-stations-detail', kwargs={'code': 'CST'})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['name'], "Central Station")

    def test_retrieve_station_invalid_code(self):
        """Test retrieving station with invalid code"""
        self.client.force_authenticate(user=self.regular_user)
        url = reverse('admin-stations-detail', kwargs={'code': 'INVALID'})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_update_station_admin_user(self):
        """Test updating station with admin user"""
        self.client.force_authenticate(user=self.admin_user)
        url = reverse('admin-stations-detail', kwargs={'code': 'CST'})
        data = {
            "name": "Updated Central Station",
            "code": "CST",
            "city": "Mumbai",
            "state": "Maharashtra"
        }
        response = self.client.put(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['name'], "Updated Central Station")

    def test_update_station_regular_user_forbidden(self):
        """Test updating station with regular user (should be forbidden)"""
        self.client.force_authenticate(user=self.regular_user)
        url = reverse('admin-stations-detail', kwargs={'code': 'CST'})
        data = {
            "name": "Updated Station",
            "code": "CST",
            "city": "Mumbai",
            "state": "Maharashtra"
        }
        response = self.client.put(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_delete_station_admin_user(self):
        """Test deleting station with admin user"""
        self.client.force_authenticate(user=self.admin_user)
        url = reverse('admin-stations-detail', kwargs={'code': 'CST'})
        response = self.client.delete(url)
        
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        # Check soft delete
        station = Station.all_objects.get(code='CST')
        self.assertFalse(station.is_active)

    def test_delete_station_regular_user_forbidden(self):
        """Test deleting station with regular user (should be forbidden)"""
        self.client.force_authenticate(user=self.regular_user)
        url = reverse('admin-stations-detail', kwargs={'code': 'CST'})
        response = self.client.delete(url)
        
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_filter_stations_by_city(self):
        """Test filtering stations by city"""
        self.client.force_authenticate(user=self.regular_user)
        url = reverse('admin-stations-list')
        response = self.client.get(url, {'city': 'Mumbai'})
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['city'], 'Mumbai')

    def test_filter_stations_by_state(self):
        """Test filtering stations by state"""
        self.client.force_authenticate(user=self.regular_user)
        url = reverse('admin-stations-list')
        response = self.client.get(url, {'state': 'Delhi'})
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['state'], 'Delhi')

    def test_assign_station_master_admin_user(self):
        """Test assigning station master with admin user"""
        self.client.force_authenticate(user=self.admin_user)
        url = reverse('admin-stations-assign-master', kwargs={'code': 'CST'})
        data = {"user_id": self.station_master.id}
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        station = Station.objects.get(code='CST')
        self.assertEqual(station.station_master, self.station_master)

    def test_assign_station_master_regular_user_forbidden(self):
        """Test assigning station master with regular user (should be forbidden)"""
        self.client.force_authenticate(user=self.regular_user)
        url = reverse('admin-stations-assign-master', kwargs={'code': 'CST'})
        data = {"user_id": self.station_master.id}
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_assign_station_master_invalid_user_id(self):
        """Test assigning station master with invalid user ID"""
        self.client.force_authenticate(user=self.admin_user)
        url = reverse('admin-stations-assign-master', kwargs={'code': 'CST'})
        data = {"user_id": 99999}  # Non-existent user
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)

    def test_assign_station_master_user_not_station_master_role(self):
        """Test assigning user who is not station master role"""
        self.client.force_authenticate(user=self.admin_user)
        url = reverse('admin-stations-assign-master', kwargs={'code': 'CST'})
        data = {"user_id": self.regular_user.id}  # Regular user, not station master
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_assign_station_master_already_assigned_user(self):
        """Test assigning station master who is already assigned to another station"""
        # First, assign station master to station1
        self.station1.station_master = self.station_master
        self.station1.save()
        
        self.client.force_authenticate(user=self.admin_user)
        url = reverse('admin-stations-assign-master', kwargs={'code': 'DLJ'})
        data = {"user_id": self.station_master.id}
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)

    def test_assign_station_master_inactive_station(self):
        """Test assigning station master to inactive station"""
        # Deactivate station
        self.station1.is_active = False
        self.station1.save()
        
        self.client.force_authenticate(user=self.admin_user)
        url = reverse('admin-stations-assign-master', kwargs={'code': 'CST'})
        data = {"user_id": self.station_master.id}
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_delete_station_with_route_edges(self):
        """Test deleting station that has route edges (junction scenario)"""
        # Create route edges
        station3 = Station.objects.create(
            name="Station 3",
            code="ST3",
            city="City 3",
            state="State 3"
        )
        
        # Create route edges: ST3 -> CST -> DLJ
        edge1 = RouteEdge.objects.create(
            from_station=station3,
            to_station=self.station1,
            distance=100,
            is_active=True
        )
        edge2 = RouteEdge.objects.create(
            from_station=self.station1,
            to_station=self.station2,
            distance=150,
            is_active=True
        )
        
        self.client.force_authenticate(user=self.admin_user)
        url = reverse('admin-stations-detail', kwargs={'code': 'CST'})
        response = self.client.delete(url)
        
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        
        # Check that station is deactivated
        station = Station.all_objects.get(code='CST')
        self.assertFalse(station.is_active)
        
        # Check that edges are deactivated
        edge1.refresh_from_db()
        edge2.refresh_from_db()
        self.assertFalse(edge1.is_active)
        self.assertFalse(edge2.is_active)
        
        # Check that new bypass edge is created
        bypass_edge = RouteEdge.objects.filter(
            from_station=station3,
            to_station=self.station2,
            is_active=True
        ).first()
        self.assertIsNotNone(bypass_edge)
        self.assertEqual(bypass_edge.distance, 250)  # 100 + 150

    def test_delete_station_complex_junction(self):
        """Test deleting station that is a complex junction (not simple pass-through)"""
        # Create multiple route edges to make it a junction
        station3 = Station.objects.create(
            name="Station 3",
            code="ST3",
            city="City 3",
            state="State 3"
        )
        station4 = Station.objects.create(
            name="Station 4",
            code="ST4",
            city="City 4",
            state="State 4"
        )
        
        # Create multiple edges to CST (making it a junction)
        RouteEdge.objects.create(
            from_station=station3,
            to_station=self.station1,
            distance=100,
            is_active=True
        )
        RouteEdge.objects.create(
            from_station=station4,
            to_station=self.station1,
            distance=120,
            is_active=True
        )
        RouteEdge.objects.create(
            from_station=self.station1,
            to_station=self.station2,
            distance=150,
            is_active=True
        )
        
        self.client.force_authenticate(user=self.admin_user)
        url = reverse('admin-stations-detail', kwargs={'code': 'CST'})
        response = self.client.delete(url)
        
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        
        # Check that station is deactivated but no bypass edge created
        station = Station.all_objects.get(code='CST')
        self.assertFalse(station.is_active)
        
        # Check that no bypass edge was created (complex junction)
        bypass_edge = RouteEdge.objects.filter(
            from_station__in=[station3, station4],
            to_station=self.station2,
            is_active=True
        ).first()
        self.assertIsNone(bypass_edge)

    def test_edge_case_empty_station_name(self):
        """Test edge case with empty station name"""
        self.client.force_authenticate(user=self.admin_user)
        url = reverse('admin-stations-list')
        data = {
            "name": "",
            "code": "TST",
            "city": "Test City",
            "state": "Test State"
        }
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_edge_case_empty_station_code(self):
        """Test edge case with empty station code"""
        self.client.force_authenticate(user=self.admin_user)
        url = reverse('admin-stations-list')
        data = {
            "name": "Test Station",
            "code": "",
            "city": "Test City",
            "state": "Test State"
        }
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_edge_case_very_long_station_name(self):
        """Test edge case with very long station name"""
        self.client.force_authenticate(user=self.admin_user)
        url = reverse('admin-stations-list')
        data = {
            "name": "A" * 101,  # Exceeds max_length
            "code": "TST",
            "city": "Test City",
            "state": "Test State"
        }
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_edge_case_special_characters_in_station_code(self):
        """Test edge case with special characters in station code"""
        self.client.force_authenticate(user=self.admin_user)
        url = reverse('admin-stations-list')
        data = {
            "name": "Test Station",
            "code": "T@ST",  # Special character
            "city": "Test City",
            "state": "Test State"
        }
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_edge_case_case_insensitive_duplicate_code(self):
        """Test edge case with case insensitive duplicate code"""
        # Create station with lowercase code
        Station.objects.create(
            name="First Station",
            code="test",
            city="Test City",
            state="Test State"
        )
        
        self.client.force_authenticate(user=self.admin_user)
        url = reverse('admin-stations-list')
        data = {
            "name": "Second Station",
            "code": "TEST",  # Same code, different case
            "city": "Test City",
            "state": "Test State"
        }
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_edge_case_inactive_station_master(self):
        """Test edge case with inactive station master"""
        # Create inactive station master
        inactive_master = User.objects.create_user(
            username="inactive_master",
            email="inactive@test.com",
            password="masterpass123",
            role="station_master",
            is_active=False  # Inactive
        )
        
        self.client.force_authenticate(user=self.admin_user)
        url = reverse('admin-stations-assign-master', kwargs={'code': 'CST'})
        data = {"user_id": inactive_master.id}
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_edge_case_station_master_already_assigned_to_same_station(self):
        """Test edge case where station master is already assigned to the same station"""
        # Assign station master to station
        self.station1.station_master = self.station_master
        self.station1.save()
        
        self.client.force_authenticate(user=self.admin_user)
        url = reverse('admin-stations-assign-master', kwargs={'code': 'CST'})
        data = {"user_id": self.station_master.id}
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_edge_case_station_already_has_different_master(self):
        """Test edge case where station already has a different master"""
        # Create another station master
        another_master = User.objects.create_user(
            username="another_master",
            email="another@test.com",
            password="masterpass123",
            role="station_master",
            is_active=True
        )
        
        # Assign different master to station
        self.station1.station_master = another_master
        self.station1.save()
        
        self.client.force_authenticate(user=self.admin_user)
        url = reverse('admin-stations-assign-master', kwargs={'code': 'CST'})
        data = {"user_id": self.station_master.id}
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_edge_case_delete_already_inactive_station(self):
        """Test edge case deleting already inactive station"""
        # Deactivate station
        self.station1.is_active = False
        self.station1.save()
        
        self.client.force_authenticate(user=self.admin_user)
        url = reverse('admin-stations-detail', kwargs={'code': 'CST'})
        response = self.client.delete(url)
        
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_edge_case_malformed_json_request(self):
        """Test edge case with malformed JSON request"""
        self.client.force_authenticate(user=self.admin_user)
        url = reverse('admin-stations-list')
        response = self.client.post(
            url, 
            '{"name": "Test Station", "code": "TST", "city": "Test City", "state": "Test State"', 
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_edge_case_missing_required_fields(self):
        """Test edge case with missing required fields"""
        self.client.force_authenticate(user=self.admin_user)
        url = reverse('admin-stations-list')
        data = {
            "name": "Test Station",
            # Missing code, city, state
        }
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_edge_case_negative_user_id(self):
        """Test edge case with negative user ID for station master assignment"""
        self.client.force_authenticate(user=self.admin_user)
        url = reverse('admin-stations-assign-master', kwargs={'code': 'CST'})
        data = {"user_id": -1}
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_edge_case_zero_user_id(self):
        """Test edge case with zero user ID for station master assignment"""
        self.client.force_authenticate(user=self.admin_user)
        url = reverse('admin-stations-assign-master', kwargs={'code': 'CST'})
        data = {"user_id": 0}
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_edge_case_string_user_id(self):
        """Test edge case with string user ID for station master assignment"""
        self.client.force_authenticate(user=self.admin_user)
        url = reverse('admin-stations-assign-master', kwargs={'code': 'CST'})
        data = {"user_id": "invalid"}
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_edge_case_unicode_station_name(self):
        """Test edge case with unicode characters in station name"""
        self.client.force_authenticate(user=self.admin_user)
        url = reverse('admin-stations-list')
        data = {
            "name": "Mumbai Central स्टेशन",  # Unicode characters
            "code": "MCS",
            "city": "Mumbai",
            "state": "Maharashtra"
        }
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_edge_case_whitespace_only_station_name(self):
        """Test edge case with whitespace-only station name"""
        self.client.force_authenticate(user=self.admin_user)
        url = reverse('admin-stations-list')
        data = {
            "name": "   ",  # Only whitespace
            "code": "TST",
            "city": "Test City",
            "state": "Test State"
        }
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_edge_case_whitespace_only_station_code(self):
        """Test edge case with whitespace-only station code"""
        self.client.force_authenticate(user=self.admin_user)
        url = reverse('admin-stations-list')
        data = {
            "name": "Test Station",
            "code": "   ",  # Only whitespace
            "city": "Test City",
            "state": "Test State"
        }
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_edge_case_sql_injection_attempt(self):
        """Test edge case with SQL injection attempt in station name"""
        self.client.force_authenticate(user=self.admin_user)
        url = reverse('admin-stations-list')
        data = {
            "name": "Test'; DROP TABLE stations; --",
            "code": "TST",
            "city": "Test City",
            "state": "Test State"
        }
        response = self.client.post(url, data, format='json')
        
        # Should be handled safely by Django ORM
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_edge_case_xss_attempt(self):
        """Test edge case with XSS attempt in station name"""
        self.client.force_authenticate(user=self.admin_user)
        url = reverse('admin-stations-list')
        data = {
            "name": "<script>alert('xss')</script>",
            "code": "TST",
            "city": "Test City",
            "state": "Test State"
        }
        response = self.client.post(url, data, format='json')
        
        # Should be handled safely by Django ORM
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_edge_case_very_large_request(self):
        """Test edge case with very large request body"""
        self.client.force_authenticate(user=self.admin_user)
        url = reverse('admin-stations-list')
        data = {
            "name": "A" * 10000,  # Very large name
            "code": "TST",
            "city": "Test City",
            "state": "Test State"
        }
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_edge_case_concurrent_station_creation(self):
        """Test edge case with concurrent station creation (race condition simulation)"""
        self.client.force_authenticate(user=self.admin_user)
        url = reverse('admin-stations-list')
        data = {
            "name": "Concurrent Station",
            "code": "CON",
            "city": "Test City",
            "state": "Test State"
        }
        
        # Simulate concurrent requests
        response1 = self.client.post(url, data, format='json')
        response2 = self.client.post(url, data, format='json')
        
        # First should succeed, second should fail due to duplicate
        self.assertEqual(response1.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response2.status_code, status.HTTP_400_BAD_REQUEST)

    def test_edge_case_station_master_role_change_after_assignment(self):
        """Test edge case where station master role changes after assignment"""
        # Assign station master
        self.station1.station_master = self.station_master
        self.station1.save()
        
        # Change role to regular user
        self.station_master.role = "user"
        self.station_master.save()
        
        # Try to retrieve station - should still work
        self.client.force_authenticate(user=self.regular_user)
        url = reverse('admin-stations-detail', kwargs={'code': 'CST'})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Note: The station_master_username should still be available in response
        self.assertIn('station_master_username', response.data)

    def test_edge_case_station_master_deactivation_after_assignment(self):
        """Test edge case where station master is deactivated after assignment"""
        # Assign station master
        self.station1.station_master = self.station_master
        self.station1.save()
        
        # Deactivate station master
        self.station_master.is_active = False
        self.station_master.save()
        
        # Try to retrieve station - should still work
        self.client.force_authenticate(user=self.regular_user)
        url = reverse('admin-stations-detail', kwargs={'code': 'CST'})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Note: The station_master_username should still be available in response
        self.assertIn('station_master_username', response.data)

    


