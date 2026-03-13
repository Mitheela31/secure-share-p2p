"""
Test script for Phase 3 & 4 implementation verification.
Tests the complete registration flow with ECDH key generation.
"""
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'secure_share.settings')
django.setup()

from django.contrib.auth import get_user_model
from users.models import UserProfile, UserPrivateKey
from users.serializers import UserRegistrationSerializer
import uuid

User = get_user_model()

def test_registration_flow():
    """Test the complete registration flow with ECDH key generation."""
    print('=' * 60)
    print('Testing Full Registration Flow with ECDH Key Generation')
    print('=' * 60)

    test_username = f'testuser_{uuid.uuid4().hex[:8]}'
    data = {
        'username': test_username,
        'email': f'{test_username}@test.com',
        'password': 'SecurePass123!',
        'password_confirm': 'SecurePass123!',
        'first_name': 'Test',
        'last_name': 'User'
    }

    serializer = UserRegistrationSerializer(data=data)
    if serializer.is_valid():
        user = serializer.save()
        print(f'\n[✓] User created: {user.username}')
        
        # Verify UserProfile with public key
        profile = UserProfile.objects.get(user=user)
        assert profile.public_key, "Public key should exist"
        print(f'[✓] Public key stored: {len(profile.public_key)} chars')
        print(f'    Starts with: {profile.public_key[:45]}...')
        
        # Verify UserPrivateKey (encrypted)
        private_key_record = UserPrivateKey.objects.get(user=user)
        assert private_key_record.encrypted_private_key, "Encrypted private key should exist"
        print(f'[✓] Private key encrypted: {len(private_key_record.encrypted_private_key)} chars')
        
        # Verify NOT stored as plaintext
        is_encrypted = not private_key_record.encrypted_private_key.startswith('-----BEGIN')
        assert is_encrypted, "Private key should be encrypted, not plaintext PEM"
        print(f'[✓] Private key is encrypted (not plaintext PEM)')
        
        # Verify decryption works
        decrypted = private_key_record.get_decrypted_private_key()
        is_valid_pem = decrypted.startswith(b'-----BEGIN PRIVATE KEY-----')
        assert is_valid_pem, "Decrypted key should be valid PEM"
        print(f'[✓] Private key decryptable to valid PEM')
        
        # Verify key_created_at is set
        assert profile.key_created_at, "Key creation timestamp should be set"
        print(f'[✓] Key created at: {profile.key_created_at}')
        
        # Cleanup
        user.delete()
        print('\n' + '=' * 60)
        print('[SUCCESS] Registration flow with ECDH keys - ALL CHECKS PASSED')
        print('=' * 60)
        return True
    else:
        print(f'[FAIL] Validation errors: {serializer.errors}')
        return False

if __name__ == '__main__':
    success = test_registration_flow()
    sys.exit(0 if success else 1)
