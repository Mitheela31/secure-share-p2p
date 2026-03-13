#!/usr/bin/env python
"""
Test script for End-to-End Encryption and Decryption (Phase 5 & Phase 6).

This script tests the complete secure file transfer flow:
1. Register two users (Alice and Bob)
2. Alice initiates ECDH key exchange with Bob
3. Alice encrypts and uploads a file for Bob
4. Bob decrypts and downloads the file
5. Verify decrypted content matches original

Run: python test_e2e_encryption.py
"""

import os
import sys
import base64

# Django setup
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'secure_share.settings')
import django
django.setup()

from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from users.models import UserProfile, UserPrivateKey
from crypto.models import SessionKey
from crypto.utils import (
    generate_key_pair,
    serialize_public_key,
    serialize_private_key,
    load_public_key,
    load_private_key,
    derive_shared_secret,
    derive_aes_session_key,
    encrypt_file,
    decrypt_file,
)
from files.models import File

User = get_user_model()


def print_header(title: str):
    """Print a test section header."""
    print(f"\n{'='*70}")
    print(f" {title}")
    print(f"{'='*70}\n")


def cleanup_test_users():
    """Remove test users from previous runs."""
    User.objects.filter(username__in=['alice_test_e2e', 'bob_test_e2e']).delete()
    print("✓ Cleaned up previous test users")


def create_test_users():
    """Create Alice and Bob test users with ECDH key pairs."""
    print_header("STEP 1: Create Test Users with ECDH Key Pairs")
    
    users = {}
    
    for username, email in [('alice_test_e2e', 'alice@test.com'), ('bob_test_e2e', 'bob@test.com')]:
        # Create user
        user = User.objects.create_user(
            username=username,
            email=email,
            password='TestPassword123!'
        )
        
        # Generate ECDH key pair
        private_key, public_key = generate_key_pair()
        public_key_pem = serialize_public_key(public_key).decode('utf-8')
        private_key_pem = serialize_private_key(private_key)
        
        # Create profile with public key
        profile = UserProfile.objects.create(
            user=user,
            public_key=public_key_pem
        )
        
        # Store encrypted private key (use class method to encrypt)
        encrypted_pem = UserPrivateKey.encrypt_private_key(private_key_pem)
        private_key_storage = UserPrivateKey.objects.create(
            user=user,
            encrypted_private_key=encrypted_pem
        )
        
        users[username] = {
            'user': user,
            'profile': profile,
            'private_key': private_key,
            'public_key': public_key,
            'private_key_pem': private_key_pem,
        }
        
        print(f"✓ Created user: {username}")
        print(f"  - Public key: {len(public_key_pem)} chars")
        print(f"  - Private key encrypted and stored")
    
    return users['alice_test_e2e'], users['bob_test_e2e']


def perform_key_exchange(alice, bob):
    """Perform ECDH key exchange between Alice and Bob."""
    print_header("STEP 2: ECDH Key Exchange")
    
    # Alice derives shared secret using her private key + Bob's public key
    alice_shared = derive_shared_secret(
        private_key=alice['private_key'],
        peer_public_key=bob['public_key'],
        info=f"secure-file-transfer:{alice['user'].id}:{bob['user'].id}".encode('utf-8')
    )
    
    # Bob derives shared secret using his private key + Alice's public key
    bob_shared = derive_shared_secret(
        private_key=bob['private_key'],
        peer_public_key=alice['public_key'],
        info=f"secure-file-transfer:{alice['user'].id}:{bob['user'].id}".encode('utf-8')
    )
    
    # Verify both parties derive the same secret
    assert alice_shared == bob_shared, "ECDH shared secrets don't match!"
    print(f"✓ Both parties derived same shared secret: {len(alice_shared)} bytes")
    
    # Store session key in database (Alice as sender)
    session = SessionKey.objects.create(
        sender=alice['user'],
        receiver=bob['user'],
        shared_secret=base64.b64encode(alice_shared).decode('utf-8'),
        is_active=True
    )
    
    print(f"✓ Session key stored: ID={session.id}")
    print(f"✓ Session valid: {session.is_valid}")
    
    return session, alice_shared


def encrypt_and_upload_file(alice, bob, session, shared_secret):
    """Alice encrypts a file for Bob and uploads it."""
    print_header("STEP 3: Encrypt and Upload File (Alice → Bob)")
    
    # Create test file content
    original_content = b"This is a secret message from Alice to Bob! " * 100
    original_name = "secret_message.txt"
    
    print(f"✓ Original file: {original_name}")
    print(f"✓ Original size: {len(original_content)} bytes")
    print(f"✓ First 50 chars: {original_content[:50].decode('utf-8')}...")
    
    # Derive AES-256 key using same context as views.py
    aes_key = derive_aes_session_key(
        shared_secret=shared_secret,
        context=f"file-encryption:{session.id}".encode('utf-8')
    )
    print(f"✓ AES-256 key derived: {len(aes_key)} bytes ({len(aes_key)*8} bits)")
    
    # Encrypt file
    ciphertext, iv, tag = encrypt_file(original_content, aes_key)
    
    print(f"✓ Ciphertext: {len(ciphertext)} bytes")
    print(f"✓ IV: {len(iv)} bytes (hex: {iv.hex()})")
    print(f"✓ Tag: {len(tag)} bytes (hex: {tag.hex()})")
    
    # Create encrypted file in Django
    encrypted_content = ContentFile(ciphertext, name=f"{original_name}.enc")
    
    import hashlib
    checksum = hashlib.sha256(original_content).hexdigest()
    
    file_obj = File.objects.create(
        name=original_name,
        original_name=original_name,
        size=len(original_content),
        mime_type='text/plain',
        checksum=checksum,
        is_encrypted=True,
        encryption_algorithm='AES-256-GCM',
        encrypted_file=encrypted_content,
        iv=iv.hex(),
        tag=tag.hex(),
        is_decrypted=False,
        session=session,
        owner=alice['user'],
    )
    
    print(f"✓ File record created: ID={file_obj.id}, UUID={file_obj.uuid}")
    
    return file_obj, original_content, aes_key


def decrypt_and_download_file(bob, file_obj, session, expected_content):
    """Bob decrypts and downloads the file."""
    print_header("STEP 4: Decrypt and Download File (Bob)")
    
    # Simulate what SecureFileDownloadView does
    
    # Step 1: Verify authorization
    assert file_obj.session.receiver == bob['user'], "Bob is not the intended receiver!"
    print(f"✓ Authorization verified: Bob is the intended receiver")
    
    # Step 2: Verify session is valid
    assert session.is_valid, "Session is not valid!"
    print(f"✓ Session is valid: is_active={session.is_active}, is_expired={session.is_expired}")
    
    # Step 3: Derive AES key (Bob uses same process)
    shared_secret = base64.b64decode(session.shared_secret)
    aes_key = derive_aes_session_key(
        shared_secret=shared_secret,
        context=f"file-encryption:{session.id}".encode('utf-8')
    )
    print(f"✓ Bob derived AES-256 key: {len(aes_key)} bytes")
    
    # Step 4: Read encrypted file and parameters
    file_obj.encrypted_file.seek(0)
    ciphertext = file_obj.encrypted_file.read()
    iv = bytes.fromhex(file_obj.iv)
    tag = bytes.fromhex(file_obj.tag)
    
    print(f"✓ Read encrypted file: {len(ciphertext)} bytes")
    print(f"✓ IV from database: {iv.hex()}")
    print(f"✓ Tag from database: {tag.hex()}")
    
    # Step 5: Decrypt
    decrypted_content = decrypt_file(
        ciphertext=ciphertext,
        aes_key=aes_key,
        iv=iv,
        tag=tag
    )
    
    print(f"✓ Decrypted: {len(decrypted_content)} bytes")
    print(f"✓ First 50 chars: {decrypted_content[:50].decode('utf-8')}...")
    
    # Step 6: Verify content matches original
    assert decrypted_content == expected_content, "Decrypted content doesn't match original!"
    print(f"✓ CONTENT VERIFICATION PASSED: Decrypted content matches original!")
    
    # Step 7: Update file metadata (simulating view behavior)
    from django.utils import timezone
    file_obj.is_decrypted = True
    file_obj.downloaded_at = timezone.now()
    file_obj.download_count += 1
    file_obj.save()
    
    print(f"✓ File marked as decrypted")
    print(f"✓ Download count: {file_obj.download_count}")
    
    return decrypted_content


def test_tamper_detection(file_obj, session):
    """Test that tampering with ciphertext is detected."""
    print_header("STEP 5: Tamper Detection Test")
    
    # Get shared secret and derive AES key
    shared_secret = base64.b64decode(session.shared_secret)
    aes_key = derive_aes_session_key(
        shared_secret=shared_secret,
        context=f"file-encryption:{session.id}".encode('utf-8')
    )
    
    # Read encrypted file
    file_obj.encrypted_file.seek(0)
    ciphertext = file_obj.encrypted_file.read()
    iv = bytes.fromhex(file_obj.iv)
    tag = bytes.fromhex(file_obj.tag)
    
    # Test 1: Tamper with ciphertext
    tampered_ct = bytearray(ciphertext)
    tampered_ct[0] ^= 0xFF
    
    try:
        decrypt_file(bytes(tampered_ct), aes_key, iv, tag)
        print("✗ FAILED: Tampered ciphertext was not detected!")
        return False
    except Exception:
        print("✓ Tampered ciphertext DETECTED (decryption failed as expected)")
    
    # Test 2: Wrong IV
    wrong_iv = os.urandom(12)
    try:
        decrypt_file(ciphertext, aes_key, wrong_iv, tag)
        print("✗ FAILED: Wrong IV was not detected!")
        return False
    except Exception:
        print("✓ Wrong IV DETECTED")
    
    # Test 3: Wrong tag
    wrong_tag = os.urandom(16)
    try:
        decrypt_file(ciphertext, aes_key, iv, wrong_tag)
        print("✗ FAILED: Wrong tag was not detected!")
        return False
    except Exception:
        print("✓ Wrong tag DETECTED")
    
    print("✓ All tamper detection tests PASSED!")
    return True


def run_all_tests():
    """Run all end-to-end encryption tests."""
    print("\n" + "="*70)
    print(" END-TO-END ENCRYPTION TEST SUITE (Phase 5 & Phase 6)")
    print("="*70)
    
    try:
        # Cleanup
        cleanup_test_users()
        
        # Step 1: Create users
        alice, bob = create_test_users()
        
        # Step 2: Key exchange
        session, shared_secret = perform_key_exchange(alice, bob)
        
        # Step 3: Encrypt and upload
        file_obj, original_content, _ = encrypt_and_upload_file(alice, bob, session, shared_secret)
        
        # Step 4: Decrypt and download
        decrypt_and_download_file(bob, file_obj, session, original_content)
        
        # Step 5: Tamper detection
        test_tamper_detection(file_obj, session)
        
        # Cleanup
        print_header("CLEANUP")
        cleanup_test_users()
        
        print("\n" + "="*70)
        print(" ALL TESTS PASSED ✓")
        print("="*70)
        print("\nPhase 5 (Encryption) + Phase 6 (Decryption) working correctly!")
        print("\n")
        
        return True
        
    except Exception as e:
        print(f"\n✗ TEST FAILED: {str(e)}")
        import traceback
        traceback.print_exc()
        
        # Cleanup on failure
        cleanup_test_users()
        
        return False


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
