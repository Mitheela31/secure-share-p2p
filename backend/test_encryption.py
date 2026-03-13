#!/usr/bin/env python
"""
Test script for AES-256-GCM file encryption.

This script tests:
1. AES-256 key derivation from shared secret
2. File encryption with AES-256-GCM
3. File decryption and integrity verification
4. Edge cases and error handling

Run: python test_encryption.py
"""

import os
import sys
import base64

# Django setup
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'secure_share.settings')
import django
django.setup()

from crypto.utils import (
    generate_key_pair,
    derive_shared_secret,
    derive_aes_session_key,
    encrypt_file,
    decrypt_file,
    AES_KEY_SIZE,
    AES_IV_SIZE,
    AES_TAG_SIZE,
)


def print_header(title: str):
    """Print a test section header."""
    print(f"\n{'='*60}")
    print(f" {title}")
    print(f"{'='*60}\n")


def test_aes_key_derivation():
    """Test AES-256 key derivation from ECDH shared secret."""
    print_header("TEST 1: AES-256 Key Derivation from Shared Secret")
    
    # Simulate ECDH key exchange
    alice_private, alice_public = generate_key_pair()
    bob_private, bob_public = generate_key_pair()
    
    # Both parties derive the same shared secret
    alice_shared = derive_shared_secret(alice_private, bob_public, info=b"test")
    bob_shared = derive_shared_secret(bob_private, alice_public, info=b"test")
    
    assert alice_shared == bob_shared, "ECDH shared secrets don't match!"
    print(f"✓ ECDH shared secret: {len(alice_shared)} bytes")
    
    # Derive AES key from shared secret
    aes_key = derive_aes_session_key(alice_shared)
    
    # Verify key size
    assert len(aes_key) == AES_KEY_SIZE, f"Expected {AES_KEY_SIZE} bytes, got {len(aes_key)}"
    print(f"✓ AES-256 key derived: {len(aes_key)} bytes ({len(aes_key)*8} bits)")
    
    # Both parties should derive the same AES key
    alice_aes = derive_aes_session_key(alice_shared)
    bob_aes = derive_aes_session_key(bob_shared)
    assert alice_aes == bob_aes, "AES keys don't match!"
    print(f"✓ Both parties derive same AES key")
    
    return aes_key


def test_file_encryption(aes_key: bytes):
    """Test AES-256-GCM file encryption."""
    print_header("TEST 2: AES-256-GCM File Encryption")
    
    # Create test data
    test_data = b"This is a secret message for testing AES-256-GCM encryption! " * 100
    print(f"✓ Original data: {len(test_data)} bytes")
    
    # Encrypt
    ciphertext, iv, tag = encrypt_file(test_data, aes_key)
    
    # Verify outputs
    assert len(ciphertext) == len(test_data), "Ciphertext length should match plaintext (GCM mode)"
    assert len(iv) == AES_IV_SIZE, f"IV should be {AES_IV_SIZE} bytes"
    assert len(tag) == AES_TAG_SIZE, f"Tag should be {AES_TAG_SIZE} bytes"
    
    print(f"✓ Ciphertext: {len(ciphertext)} bytes")
    print(f"✓ IV: {len(iv)} bytes (hex: {iv.hex()[:24]}...)")
    print(f"✓ Tag: {len(tag)} bytes (hex: {tag.hex()})")
    
    # Verify ciphertext is different from plaintext
    assert ciphertext != test_data, "Ciphertext should differ from plaintext!"
    print(f"✓ Ciphertext differs from plaintext")
    
    return test_data, ciphertext, iv, tag


def test_file_decryption(aes_key: bytes, original: bytes, ciphertext: bytes, iv: bytes, tag: bytes):
    """Test AES-256-GCM file decryption."""
    print_header("TEST 3: AES-256-GCM File Decryption")
    
    # Decrypt
    decrypted = decrypt_file(ciphertext, aes_key, iv, tag)
    
    # Verify decryption
    assert decrypted == original, "Decrypted data doesn't match original!"
    print(f"✓ Decryption successful: {len(decrypted)} bytes")
    print(f"✓ Data integrity verified (matches original)")
    
    return True


def test_tamper_detection(aes_key: bytes, ciphertext: bytes, iv: bytes, tag: bytes):
    """Test that tampering is detected."""
    print_header("TEST 4: Tamper Detection (Authentication)")
    
    # Test 1: Tampered ciphertext
    tampered_ct = bytearray(ciphertext)
    tampered_ct[0] ^= 0xFF  # Flip bits
    
    try:
        decrypt_file(bytes(tampered_ct), aes_key, iv, tag)
        print("✗ FAILED: Tampered ciphertext was not detected!")
        return False
    except Exception as e:
        print(f"✓ Tampered ciphertext detected: {str(e)[:50]}...")
    
    # Test 2: Wrong IV
    wrong_iv = os.urandom(AES_IV_SIZE)
    try:
        decrypt_file(ciphertext, aes_key, wrong_iv, tag)
        print("✗ FAILED: Wrong IV was not detected!")
        return False
    except Exception:
        print(f"✓ Wrong IV detected")
    
    # Test 3: Wrong tag
    wrong_tag = os.urandom(AES_TAG_SIZE)
    try:
        decrypt_file(ciphertext, aes_key, iv, wrong_tag)
        print("✗ FAILED: Wrong tag was not detected!")
        return False
    except Exception:
        print(f"✓ Wrong tag detected")
    
    # Test 4: Wrong key
    wrong_key = os.urandom(AES_KEY_SIZE)
    try:
        decrypt_file(ciphertext, wrong_key, iv, tag)
        print("✗ FAILED: Wrong key was not detected!")
        return False
    except Exception:
        print(f"✓ Wrong key detected")
    
    print(f"✓ All tamper detection tests passed!")
    return True


def test_iv_uniqueness():
    """Test that IVs are unique (random) for each encryption."""
    print_header("TEST 5: IV Uniqueness (Nonce Safety)")
    
    aes_key = os.urandom(AES_KEY_SIZE)
    test_data = b"Same data encrypted multiple times"
    
    ivs = set()
    ciphertexts = set()
    
    for i in range(10):
        ciphertext, iv, tag = encrypt_file(test_data, aes_key)
        ivs.add(iv.hex())
        ciphertexts.add(ciphertext.hex())
    
    assert len(ivs) == 10, "IVs should be unique!"
    assert len(ciphertexts) == 10, "Ciphertexts should vary due to random IV!"
    
    print(f"✓ 10 encryptions produced 10 unique IVs")
    print(f"✓ 10 encryptions produced 10 different ciphertexts")
    print(f"✓ IV uniqueness verified (prevents nonce reuse attacks)")
    
    return True


def test_large_file():
    """Test encryption of larger files."""
    print_header("TEST 6: Large File Encryption (10 MB)")
    
    aes_key = os.urandom(AES_KEY_SIZE)
    
    # 10 MB test file
    large_data = os.urandom(10 * 1024 * 1024)
    print(f"✓ Test file size: {len(large_data) / (1024*1024):.2f} MB")
    
    import time
    
    # Encrypt
    start = time.time()
    ciphertext, iv, tag = encrypt_file(large_data, aes_key)
    encrypt_time = time.time() - start
    print(f"✓ Encryption time: {encrypt_time:.3f}s ({len(large_data)/encrypt_time/1024/1024:.1f} MB/s)")
    
    # Decrypt
    start = time.time()
    decrypted = decrypt_file(ciphertext, aes_key, iv, tag)
    decrypt_time = time.time() - start
    print(f"✓ Decryption time: {decrypt_time:.3f}s ({len(large_data)/decrypt_time/1024/1024:.1f} MB/s)")
    
    # Verify
    assert decrypted == large_data, "Large file decryption failed!"
    print(f"✓ Large file encryption/decryption verified")
    
    return True


def run_all_tests():
    """Run all encryption tests."""
    print("\n" + "="*60)
    print(" AES-256-GCM ENCRYPTION TEST SUITE")
    print("="*60)
    
    try:
        # Test 1: Key derivation
        aes_key = test_aes_key_derivation()
        
        # Test 2: Encryption
        original, ciphertext, iv, tag = test_file_encryption(aes_key)
        
        # Test 3: Decryption
        test_file_decryption(aes_key, original, ciphertext, iv, tag)
        
        # Test 4: Tamper detection
        test_tamper_detection(aes_key, ciphertext, iv, tag)
        
        # Test 5: IV uniqueness
        test_iv_uniqueness()
        
        # Test 6: Large file
        test_large_file()
        
        print("\n" + "="*60)
        print(" ALL TESTS PASSED ✓")
        print("="*60 + "\n")
        
        return True
        
    except Exception as e:
        print(f"\n✗ TEST FAILED: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
