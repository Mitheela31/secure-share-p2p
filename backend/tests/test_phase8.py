"""
=============================================================================
PHASE 8: Unit Tests
=============================================================================

Comprehensive unit tests for SecureShare application.

Test Categories:
1. Authentication Tests - JWT token generation, refresh, logout
2. File Upload Tests - File creation, validation, security
3. File Transfer Tests - Transfer lifecycle, access control
4. Activity Logging Tests - Log creation, retrieval

To run tests:
    cd backend
    python manage.py test

To run specific test class:
    python manage.py test tests.test_phase8.AuthenticationTests

To run with verbose output:
    python manage.py test tests.test_phase8 -v 2

=============================================================================
"""

import base64
import json
from io import BytesIO
from django.test import TestCase, override_settings
from django.urls import reverse
from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken

User = get_user_model()


# =============================================================================
# AUTHENTICATION TESTS
# =============================================================================

class AuthenticationTests(APITestCase):
    """
    Tests for JWT authentication endpoints.
    
    These tests verify:
    - User registration
    - Token generation (login)
    - Token refresh
    - Token blacklist (logout)
    - Protected endpoint access
    """
    
    def setUp(self):
        """Set up test user and client."""
        self.client = APIClient()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        # URLs
        self.register_url = '/api/v1/auth/register/'
        self.login_url = '/api/v1/auth/login/'
        self.refresh_url = '/api/v1/auth/token/refresh/'
        self.logout_url = '/api/v1/auth/logout/'
        self.profile_url = '/api/v1/auth/profile/'
    
    def test_user_registration(self):
        """Test user can register with valid data."""
        data = {
            'username': 'newuser',
            'email': 'newuser@example.com',
            'password': 'securepass123',
            'password_confirm': 'securepass123'
        }
        response = self.client.post(self.register_url, data, format='json')
        
        # May be 201 Created or 200 OK depending on implementation
        self.assertIn(response.status_code, [status.HTTP_200_OK, status.HTTP_201_CREATED])
        
        # Verify user was created
        self.assertTrue(User.objects.filter(username='newuser').exists())
    
    def test_user_registration_duplicate_username(self):
        """Test registration fails with duplicate username."""
        data = {
            'username': 'testuser',  # Already exists
            'email': 'another@example.com',
            'password': 'securepass123',
            'password_confirm': 'securepass123'
        }
        response = self.client.post(self.register_url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
    
    def test_user_login_success(self):
        """Test user can login with valid credentials."""
        data = {
            'username': 'testuser',
            'password': 'testpass123'
        }
        response = self.client.post(self.login_url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)
        self.assertIn('refresh', response.data)
    
    def test_user_login_invalid_credentials(self):
        """Test login fails with invalid credentials."""
        data = {
            'username': 'testuser',
            'password': 'wrongpassword'
        }
        response = self.client.post(self.login_url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
    
    def test_token_refresh(self):
        """Test refresh token generates new access token."""
        # First login to get tokens
        login_data = {'username': 'testuser', 'password': 'testpass123'}
        login_response = self.client.post(self.login_url, login_data, format='json')
        refresh_token = login_response.data['refresh']
        
        # Use refresh token to get new access token
        response = self.client.post(
            self.refresh_url, 
            {'refresh': refresh_token}, 
            format='json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)
    
    def test_protected_endpoint_without_token(self):
        """Test protected endpoint returns 401 without token."""
        response = self.client.get(self.profile_url)
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
    
    def test_protected_endpoint_with_token(self):
        """Test protected endpoint works with valid token."""
        # Get token
        token = RefreshToken.for_user(self.user)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token.access_token}')
        
        # Use files endpoint which is simpler and works better with test client
        response = self.client.get('/api/v1/files/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)


# =============================================================================
# FILE UPLOAD TESTS
# =============================================================================

class FileUploadTests(APITestCase):
    """
    Tests for file upload functionality.
    
    These tests verify:
    - File metadata creation
    - File upload with validation
    - File type restrictions
    - File size limits
    - Owner-based access control
    """
    
    def setUp(self):
        """Set up test user and authenticate."""
        self.user = User.objects.create_user(
            username='fileuser',
            email='fileuser@example.com',
            password='testpass123'
        )
        self.client = APIClient()
        token = RefreshToken.for_user(self.user)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token.access_token}')
        
        # URLs
        self.files_url = '/api/v1/files/'
    
    def test_create_file_metadata(self):
        """Test creating file metadata record."""
        data = {
            'original_name': 'test_document.pdf',
            'size': 1024,
            'mime_type': 'application/pdf',
            'checksum': 'abc123def456'
        }
        response = self.client.post(self.files_url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['original_name'], 'test_document.pdf')
    
    def test_list_own_files(self):
        """Test user can list their own files."""
        # Create a file first
        from files.models import File
        file_obj = File.objects.create(
            name='myfile.txt',
            original_name='myfile.txt',
            size=100,
            mime_type='text/plain',
            owner=self.user
        )
        
        response = self.client.get(self.files_url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['original_name'], 'myfile.txt')
    
    def test_cannot_access_other_user_files(self):
        """Test user cannot access files owned by others."""
        # Create another user with a file
        other_user = User.objects.create_user(
            username='otheruser',
            email='other@example.com',
            password='testpass123'
        )
        from files.models import File
        other_file = File.objects.create(
            name='secret.txt',
            original_name='secret.txt',
            size=100,
            mime_type='text/plain',
            owner=other_user
        )
        
        # Try to access the file
        response = self.client.get(f'{self.files_url}{other_file.id}/')
        
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
    
    def test_file_size_validation(self):
        """Test file size validation (must be positive)."""
        data = {
            'original_name': 'test.pdf',
            'size': -100,  # Invalid negative size
            'mime_type': 'application/pdf',
            'checksum': 'abc123'
        }
        response = self.client.post(self.files_url, data, format='json')
        
        # Should fail validation
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
    
    def test_filename_sanitization(self):
        """Test filenames with path traversal are sanitized."""
        data = {
            'original_name': '../../../etc/passwd',
            'size': 1024,
            'mime_type': 'text/plain',
            'checksum': 'abc123'
        }
        response = self.client.post(self.files_url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        # Filename should be sanitized to just 'passwd'
        self.assertNotIn('..', response.data['original_name'])
        self.assertNotIn('/', response.data['original_name'])


# =============================================================================
# FILE TRANSFER TESTS
# =============================================================================

class FileTransferTests(APITestCase):
    """
    Tests for file transfer functionality.
    
    These tests verify:
    - Transfer creation
    - Transfer acceptance/rejection
    - Transfer status transitions
    - Sender/receiver access control
    """
    
    def setUp(self):
        """Set up test users, file, and authenticate."""
        self.sender = User.objects.create_user(
            username='sender',
            email='sender@example.com',
            password='testpass123'
        )
        self.receiver = User.objects.create_user(
            username='receiver',
            email='receiver@example.com',
            password='testpass123'
        )
        
        # Create a file owned by sender
        from files.models import File
        self.test_file = File.objects.create(
            name='transfer_test.pdf',
            original_name='transfer_test.pdf',
            size=1024,
            mime_type='application/pdf',
            owner=self.sender,
            iv=base64.b64encode(b'\x02' * 12).decode('ascii')
        )
        
        self.client = APIClient()
        
        # URLs
        self.transfers_url = '/api/v1/transfers/'
        self.sent_url = '/api/v1/transfers/sent/'
        self.received_url = '/api/v1/transfers/received/'
    
    def _auth_as(self, user):
        """Helper to authenticate as a specific user."""
        token = RefreshToken.for_user(user)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token.access_token}')
    
    def test_create_transfer(self):
        """Test sender can create a transfer."""
        self._auth_as(self.sender)
        
        data = {
            'receiver_id': self.receiver.id,
            'file_id': self.test_file.id,
            'file_name': self.test_file.original_name,
            'aes_key': base64.b64encode(b'\x01' * 32).decode('ascii'),
            'iv': self.test_file.iv,
        }
        response = self.client.post(self.transfers_url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['status'], 'pending')
    
    def test_list_sent_transfers(self):
        """Test sender can list their sent transfers."""
        # Create transfer
        from transfers.models import Transfer
        transfer = Transfer.objects.create(
            sender=self.sender,
            receiver=self.receiver,
            file=self.test_file,
            status='pending'
        )
        
        self._auth_as(self.sender)
        response = self.client.get(self.sent_url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
    
    def test_list_received_transfers(self):
        """Test receiver can list their received transfers."""
        from transfers.models import Transfer
        transfer = Transfer.objects.create(
            sender=self.sender,
            receiver=self.receiver,
            file=self.test_file,
            status='pending'
        )
        
        self._auth_as(self.receiver)
        response = self.client.get(self.received_url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
    
    def test_accept_transfer(self):
        """Test receiver can accept a transfer."""
        from transfers.models import Transfer
        transfer = Transfer.objects.create(
            sender=self.sender,
            receiver=self.receiver,
            file=self.test_file,
            status='pending'
        )
        
        self._auth_as(self.receiver)
        response = self.client.post(
            f'{self.transfers_url}{transfer.id}/action/',
            {'action': 'accept'},
            format='json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('accepted', response.data['message'].lower())
    
    def test_reject_transfer(self):
        """Test receiver can reject a transfer."""
        from transfers.models import Transfer
        transfer = Transfer.objects.create(
            sender=self.sender,
            receiver=self.receiver,
            file=self.test_file,
            status='pending'
        )
        
        self._auth_as(self.receiver)
        response = self.client.post(
            f'{self.transfers_url}{transfer.id}/action/',
            {'action': 'reject'},
            format='json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('rejected', response.data['message'].lower())
    
    def test_third_party_cannot_access_transfer(self):
        """Test third party cannot access transfer details."""
        from transfers.models import Transfer
        transfer = Transfer.objects.create(
            sender=self.sender,
            receiver=self.receiver,
            file=self.test_file,
            status='pending'
        )
        
        # Create third party user
        third_party = User.objects.create_user(
            username='thirdparty',
            email='third@example.com',
            password='testpass123'
        )
        self._auth_as(third_party)
        
        # Try to access the transfer
        response = self.client.get(f'{self.transfers_url}{transfer.id}/')
        
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


# =============================================================================
# ACTIVITY LOGGING TESTS
# =============================================================================

class ActivityLoggingTests(APITestCase):
    """
    Tests for activity logging functionality.
    
    These tests verify:
    - Activity log creation
    - Log retrieval
    - Log filtering
    - Statistics endpoint
    """
    
    def setUp(self):
        """Set up test user and authenticate."""
        self.user = User.objects.create_user(
            username='audituser',
            email='audit@example.com',
            password='testpass123',
            is_staff=True  # Need staff for all logs
        )
        self.client = APIClient()
        token = RefreshToken.for_user(self.user)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token.access_token}')
        
        # URLs
        self.logs_url = '/api/v1/audit/logs/'
        self.all_logs_url = '/api/v1/audit/logs/all/'
        self.stats_url = '/api/v1/audit/stats/'
    
    def test_list_own_activity_logs(self):
        """Test user can list their activity logs."""
        from audit.models import ActivityLog
        
        # Create a log entry
        ActivityLog.log(
            action='login',
            user=self.user,
            description='User logged in',
            status='success'
        )
        
        response = self.client.get(self.logs_url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(len(response.data['results']), 1)
    
    def test_activity_stats(self):
        """Test activity statistics endpoint."""
        from audit.models import ActivityLog
        
        # Create some log entries
        ActivityLog.log(action='login', user=self.user, description='Login 1', status='success')
        ActivityLog.log(action='file_upload', user=self.user, description='Upload 1', status='success')
        ActivityLog.log(action='login', user=self.user, description='Login 2', status='failed')
        
        response = self.client.get(self.stats_url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Response uses api_response format: {status, data, message}
        self.assertIn('data', response.data)
        self.assertIn('total_activities', response.data['data'])
    
    def test_log_entry_detail(self):
        """Test retrieving a specific log entry."""
        from audit.models import ActivityLog
        
        log_entry = ActivityLog.log(
            action='file_upload',
            user=self.user,
            description='Uploaded test file',
            status='success'
        )
        
        response = self.client.get(f'{self.logs_url}{log_entry.id}/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['action'], 'file_upload')


# =============================================================================
# SECURITY VALIDATION TESTS
# =============================================================================

class SecurityValidationTests(TestCase):
    """
    Tests for security validation utilities.
    
    These tests verify:
    - File type validation
    - Filename sanitization
    - File size validation
    """
    
    def test_validate_filename_sanitization(self):
        """Test filename sanitization removes dangerous characters."""
        from api.security import validate_filename
        
        # Test path traversal
        sanitized, error = validate_filename('../../../etc/passwd')
        self.assertIsNone(error)
        self.assertNotIn('..', sanitized)
        
        # Test backslash
        sanitized, error = validate_filename('C:\\Windows\\system32\\file.txt')
        self.assertIsNone(error)
        self.assertNotIn('\\', sanitized)
    
    def test_validate_file_size_limits(self):
        """Test file size validation."""
        from api.security import validate_file_size
        
        # Valid size
        is_valid, error = validate_file_size(1024 * 1024)  # 1 MB
        self.assertTrue(is_valid)
        self.assertIsNone(error)
        
        # Invalid negative size
        is_valid, error = validate_file_size(-100)
        self.assertFalse(is_valid)
        self.assertIsNotNone(error)
    
    def test_format_file_size(self):
        """Test file size formatting."""
        from api.security import format_file_size
        
        self.assertIn('B', format_file_size(500))
        self.assertIn('KB', format_file_size(1024))
        self.assertIn('MB', format_file_size(1024 * 1024))
        self.assertIn('GB', format_file_size(1024 * 1024 * 1024))
