"""
Cryptographic Utilities for Secure P2P File Transfer.

Architecture:
============
This module implements the cryptographic building blocks:

1. ECDH Key Exchange (SECP256R1/P-256):
   - Generate ephemeral key pairs
   - Exchange public keys
   - Derive shared secret
   
2. HKDF Key Derivation (SHA-256):
   - Derive AES-256 key from shared secret
   - Uses context-specific info for key separation
   
3. AES-256-GCM Encryption:
   - Authenticated encryption with associated data
   - 12-byte IV (nonce)
   - 16-byte authentication tag

Security Properties:
==================
- Perfect Forward Secrecy: Each session uses new ephemeral keys
- Authenticated Encryption: GCM provides integrity + confidentiality
- Key Separation: HKDF derives unique keys per session

Security Rules:
===============
- NEVER log or store private keys
- NEVER reuse IVs with the same key
- ALWAYS verify authentication tag
- CLEAR sensitive memory when possible
"""

import os
import secrets
import logging
from typing import Tuple, Optional
from dataclasses import dataclass

# Cryptography library imports
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.backends import default_backend

# Configure logging (never log sensitive data)
logger = logging.getLogger(__name__)

# Constants
CURVE = ec.SECP256R1()  # NIST P-256
AES_KEY_SIZE = 32  # 256 bits
IV_SIZE = 12  # 96 bits for GCM
TAG_SIZE = 16  # 128 bits


@dataclass
class KeyPair:
    """
    ECDH Key Pair container.
    
    Attributes:
        private_key: EC private key object (NEVER expose)
        public_key: EC public key object (safe to share)
        public_key_bytes: Serialized public key for transmission
    """
    private_key: ec.EllipticCurvePrivateKey
    public_key: ec.EllipticCurvePublicKey
    public_key_bytes: bytes
    
    def __del__(self):
        """Attempt to clear sensitive data on deletion."""
        try:
            # Python doesn't guarantee memory clearing, but we try
            del self.private_key
        except Exception:
            pass


@dataclass  
class EncryptedData:
    """
    Container for encrypted data and parameters.
    
    Attributes:
        iv: Initialization vector (12 bytes)
        tag: Authentication tag (16 bytes)
        ciphertext: Encrypted data
    """
    iv: bytes
    tag: bytes
    ciphertext: bytes
    
    def to_bytes(self) -> bytes:
        """
        Serialize encrypted data for transmission.
        
        Format: [IV (12)][TAG (16)][CIPHERTEXT (variable)]
        """
        return self.iv + self.tag + self.ciphertext
    
    @classmethod
    def from_bytes(cls, data: bytes) -> 'EncryptedData':
        """
        Deserialize encrypted data from transmission.
        
        Args:
            data: Serialized encrypted data
            
        Returns:
            EncryptedData instance
            
        Raises:
            ValueError: If data is too short
        """
        if len(data) < IV_SIZE + TAG_SIZE:
            raise ValueError("Encrypted data too short")
            
        return cls(
            iv=data[:IV_SIZE],
            tag=data[IV_SIZE:IV_SIZE + TAG_SIZE],
            ciphertext=data[IV_SIZE + TAG_SIZE:]
        )


# =============================================================================
# ECDH Key Exchange Functions
# =============================================================================

def generate_key_pair() -> KeyPair:
    """
    Generate a new ECDH key pair using SECP256R1 curve.
    
    Returns:
        KeyPair containing private key, public key, and serialized public key
        
    Security Note:
        The private key must NEVER be transmitted or logged.
        Only the public_key_bytes should be sent to the peer.
    """
    # Generate ephemeral private key
    private_key = ec.generate_private_key(CURVE, default_backend())
    public_key = private_key.public_key()
    
    # Serialize public key for transmission
    public_key_bytes = public_key.public_bytes(
        encoding=serialization.Encoding.X962,
        format=serialization.PublicFormat.CompressedPoint
    )
    
    logger.debug(f"Generated ECDH key pair (public key: {len(public_key_bytes)} bytes)")
    
    return KeyPair(
        private_key=private_key,
        public_key=public_key,
        public_key_bytes=public_key_bytes
    )


def load_peer_public_key(public_key_bytes: bytes) -> ec.EllipticCurvePublicKey:
    """
    Load a peer's public key from serialized bytes.
    
    Args:
        public_key_bytes: X962 compressed point format public key
        
    Returns:
        EC public key object
        
    Raises:
        ValueError: If public key is invalid
    """
    try:
        public_key = ec.EllipticCurvePublicKey.from_encoded_point(
            CURVE, public_key_bytes
        )
        logger.debug("Loaded peer public key successfully")
        return public_key
    except Exception as e:
        logger.error(f"Invalid peer public key: {e}")
        raise ValueError(f"Invalid peer public key: {e}")


def derive_shared_secret(
    private_key: ec.EllipticCurvePrivateKey,
    peer_public_key: ec.EllipticCurvePublicKey
) -> bytes:
    """
    Derive shared secret using ECDH.
    
    Args:
        private_key: Our private key
        peer_public_key: Peer's public key
        
    Returns:
        Raw shared secret bytes (32 bytes for P-256)
        
    Security Note:
        The shared secret should NOT be used directly as an encryption key.
        Always use HKDF to derive the actual encryption key.
    """
    shared_key = private_key.exchange(ec.ECDH(), peer_public_key)
    logger.debug(f"Derived shared secret ({len(shared_key)} bytes)")
    return shared_key


# =============================================================================
# HKDF Key Derivation Functions
# =============================================================================

def derive_aes_key(
    shared_secret: bytes,
    info: bytes = b"secure-p2p-file-transfer",
    salt: Optional[bytes] = None
) -> bytes:
    """
    Derive AES-256 key from shared secret using HKDF-SHA256.
    
    Args:
        shared_secret: Raw ECDH shared secret
        info: Context-specific info string for key separation
        salt: Optional salt (if None, uses zero-filled salt)
        
    Returns:
        32-byte AES-256 key
        
    HKDF provides:
        - Key stretching/compression
        - Domain separation via info parameter
        - Randomness extraction
    """
    hkdf = HKDF(
        algorithm=hashes.SHA256(),
        length=AES_KEY_SIZE,
        salt=salt,
        info=info,
        backend=default_backend()
    )
    
    aes_key = hkdf.derive(shared_secret)
    logger.debug(f"Derived AES-256 key ({len(aes_key)} bytes)")
    return aes_key


# =============================================================================
# AES-256-GCM Encryption/Decryption Functions
# =============================================================================

def generate_iv() -> bytes:
    """
    Generate a cryptographically secure random IV for AES-GCM.
    
    Returns:
        12-byte random IV
        
    Security Note:
        NEVER reuse an IV with the same key.
        Each encryption operation MUST use a fresh IV.
    """
    return secrets.token_bytes(IV_SIZE)


def encrypt_data(plaintext: bytes, aes_key: bytes, aad: Optional[bytes] = None) -> EncryptedData:
    """
    Encrypt data using AES-256-GCM.
    
    Args:
        plaintext: Data to encrypt
        aes_key: 32-byte AES-256 key
        aad: Optional additional authenticated data
        
    Returns:
        EncryptedData containing IV, tag, and ciphertext
        
    Security Properties:
        - Confidentiality: Data is encrypted
        - Integrity: Tag verifies data wasn't tampered
        - Authentication: Tag verifies data came from key holder
    """
    if len(aes_key) != AES_KEY_SIZE:
        raise ValueError(f"AES key must be {AES_KEY_SIZE} bytes")
        
    # Generate unique IV
    iv = generate_iv()
    
    # Create cipher and encrypt
    aesgcm = AESGCM(aes_key)
    
    # GCM produces ciphertext with tag appended
    ciphertext_with_tag = aesgcm.encrypt(iv, plaintext, aad)
    
    # Split ciphertext and tag
    ciphertext = ciphertext_with_tag[:-TAG_SIZE]
    tag = ciphertext_with_tag[-TAG_SIZE:]
    
    logger.debug(f"Encrypted {len(plaintext)} bytes -> {len(ciphertext)} bytes ciphertext")
    
    return EncryptedData(iv=iv, tag=tag, ciphertext=ciphertext)


def decrypt_data(
    encrypted: EncryptedData,
    aes_key: bytes,
    aad: Optional[bytes] = None
) -> bytes:
    """
    Decrypt data using AES-256-GCM.
    
    Args:
        encrypted: EncryptedData containing IV, tag, and ciphertext
        aes_key: 32-byte AES-256 key
        aad: Optional additional authenticated data (must match encryption)
        
    Returns:
        Decrypted plaintext
        
    Raises:
        ValueError: If decryption fails (wrong key or tampered data)
        
    Security Note:
        Decryption failure indicates either:
        - Wrong key
        - Tampered ciphertext
        - Tampered IV
        - Tampered tag
        - Wrong AAD
    """
    if len(aes_key) != AES_KEY_SIZE:
        raise ValueError(f"AES key must be {AES_KEY_SIZE} bytes")
        
    # Create cipher
    aesgcm = AESGCM(aes_key)
    
    # Reconstruct ciphertext with tag for GCM
    ciphertext_with_tag = encrypted.ciphertext + encrypted.tag
    
    try:
        plaintext = aesgcm.decrypt(encrypted.iv, ciphertext_with_tag, aad)
        logger.debug(f"Decrypted {len(encrypted.ciphertext)} bytes -> {len(plaintext)} bytes")
        return plaintext
        
    except Exception as e:
        logger.error(f"Decryption failed: {e}")
        raise ValueError("Decryption failed - data may be corrupted or tampered")


# =============================================================================
# High-Level Key Exchange Protocol
# =============================================================================

class SecureKeyExchange:
    """
    High-level ECDH key exchange manager.
    
    Handles the complete key exchange process:
    1. Generate local key pair
    2. Exchange public keys
    3. Derive shared AES key
    
    Usage:
        # On both sides:
        exchange = SecureKeyExchange()
        
        # Get public key to send to peer
        my_public_key = exchange.get_public_key_bytes()
        
        # Set peer's public key and derive shared key
        exchange.set_peer_public_key(peer_public_key_bytes)
        
        # Get derived AES key
        aes_key = exchange.get_aes_key()
    """
    
    def __init__(self, context: bytes = b"secure-p2p-file-transfer"):
        """
        Initialize key exchange.
        
        Args:
            context: HKDF info string for key derivation
        """
        self._context = context
        self._key_pair: Optional[KeyPair] = None
        self._peer_public_key: Optional[ec.EllipticCurvePublicKey] = None
        self._aes_key: Optional[bytes] = None
        
    def initialize(self):
        """Generate local key pair."""
        self._key_pair = generate_key_pair()
        logger.info("Key exchange initialized - key pair generated")
        
    def get_public_key_bytes(self) -> bytes:
        """
        Get serialized public key for transmission to peer.
        
        Returns:
            Public key bytes (X962 compressed format)
            
        Raises:
            RuntimeError: If not initialized
        """
        if not self._key_pair:
            raise RuntimeError("Key exchange not initialized")
        return self._key_pair.public_key_bytes
        
    def set_peer_public_key(self, public_key_bytes: bytes):
        """
        Set peer's public key and derive shared AES key.
        
        Args:
            public_key_bytes: Peer's serialized public key
            
        Raises:
            RuntimeError: If not initialized
            ValueError: If peer public key is invalid
        """
        if not self._key_pair:
            raise RuntimeError("Key exchange not initialized")
            
        # Load peer's public key
        self._peer_public_key = load_peer_public_key(public_key_bytes)
        
        # Derive shared secret
        shared_secret = derive_shared_secret(
            self._key_pair.private_key,
            self._peer_public_key
        )
        
        # Derive AES key using HKDF
        self._aes_key = derive_aes_key(shared_secret, info=self._context)
        
        # Clear shared secret from memory
        del shared_secret
        
        logger.info("Peer public key set - AES key derived")
        
    def get_aes_key(self) -> bytes:
        """
        Get derived AES-256 key for encryption/decryption.
        
        Returns:
            32-byte AES key
            
        Raises:
            RuntimeError: If key exchange not complete
        """
        if not self._aes_key:
            raise RuntimeError("Key exchange not complete - no AES key available")
        return self._aes_key
        
    def is_complete(self) -> bool:
        """Check if key exchange is complete."""
        return self._aes_key is not None
        
    def clear(self):
        """Clear all sensitive data."""
        if self._key_pair:
            del self._key_pair
            self._key_pair = None
        if self._aes_key:
            # Overwrite with zeros (best effort)
            self._aes_key = b'\x00' * len(self._aes_key)
            self._aes_key = None
        self._peer_public_key = None
        logger.debug("Key exchange data cleared")


# =============================================================================
# Test / Demo
# =============================================================================

if __name__ == "__main__":
    print("=" * 60)
    print("Cryptographic Utilities Test")
    print("=" * 60)
    
    # Test ECDH key exchange
    print("\n1. Testing ECDH Key Exchange...")
    
    # Alice generates her key pair
    alice = SecureKeyExchange(context=b"test-context")
    alice.initialize()
    alice_public = alice.get_public_key_bytes()
    print(f"   Alice public key: {len(alice_public)} bytes")
    
    # Bob generates his key pair
    bob = SecureKeyExchange(context=b"test-context")
    bob.initialize()
    bob_public = bob.get_public_key_bytes()
    print(f"   Bob public key: {len(bob_public)} bytes")
    
    # Exchange public keys and derive shared secrets
    alice.set_peer_public_key(bob_public)
    bob.set_peer_public_key(alice_public)
    
    # Verify both derived the same key
    assert alice.get_aes_key() == bob.get_aes_key(), "Keys don't match!"
    print(f"   ✓ Both parties derived identical AES-256 key")
    print(f"   Key size: {len(alice.get_aes_key())} bytes (256 bits)")
    
    # Test encryption/decryption
    print("\n2. Testing AES-256-GCM Encryption...")
    
    test_data = b"This is a secret message for secure P2P transfer!"
    aes_key = alice.get_aes_key()
    
    # Encrypt with Alice's key
    encrypted = encrypt_data(test_data, aes_key)
    print(f"   Original: {len(test_data)} bytes")
    print(f"   IV: {encrypted.iv.hex()}")
    print(f"   Tag: {encrypted.tag.hex()}")
    print(f"   Ciphertext: {len(encrypted.ciphertext)} bytes")
    
    # Decrypt with Bob's key
    decrypted = decrypt_data(encrypted, bob.get_aes_key())
    assert decrypted == test_data, "Decryption failed!"
    print(f"   ✓ Decryption successful")
    print(f"   Decrypted: {decrypted.decode()}")
    
    # Test tamper detection
    print("\n3. Testing Tamper Detection...")
    
    # Modify ciphertext
    tampered = EncryptedData(
        iv=encrypted.iv,
        tag=encrypted.tag,
        ciphertext=bytes([encrypted.ciphertext[0] ^ 0xFF]) + encrypted.ciphertext[1:]
    )
    
    try:
        decrypt_data(tampered, aes_key)
        print("   ✗ Tamper detection failed!")
    except ValueError:
        print("   ✓ Tampered data detected (decryption failed as expected)")
    
    # Cleanup
    alice.clear()
    bob.clear()
    
    print("\n" + "=" * 60)
    print("All tests passed!")
    print("=" * 60)
