"""
Production-ready ECDH and AES-GCM encryption utilities using Python cryptography library.

This module provides:
1. ECDH (Elliptic Curve Diffie-Hellman) key exchange utilities
2. AES-256-GCM authenticated encryption for files

AES-GCM (Galois/Counter Mode) Flow:
1. Derive AES-256 key from ECDH shared secret using HKDF
2. Generate cryptographically secure random 96-bit (12 byte) IV/nonce
3. Encrypt plaintext -> ciphertext with authentication tag
4. Store: ciphertext + IV + tag (all needed for decryption)

Security Properties:
- Confidentiality: AES-256 encryption
- Integrity: GCM authentication tag
- Authenticity: Tag verification prevents tampering
- Nonce uniqueness: Random IV for each encryption
"""

from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.hazmat.backends import default_backend
import os
import base64

# ==============================================================================
# AES-GCM ENCRYPTION CONSTANTS
# ==============================================================================

AES_KEY_SIZE = 32  # 256 bits
AES_IV_SIZE = 12   # 96 bits (recommended for GCM)
AES_TAG_SIZE = 16  # 128 bits (GCM default)



def generate_key_pair() -> tuple:
    """
    Generate a new ECDH key pair using SECP256R1 curve.
    
    ECDH Flow Step 1: Generate asymmetric key pairs for both parties.
    
    Returns:
        tuple: (private_key, public_key) objects
        
    Raises:
        Exception: If key generation fails
    """
    try:
        private_key = ec.generate_private_key(
            ec.SECP256R1(), 
            backend=default_backend()
        )
        public_key = private_key.public_key()
        return private_key, public_key
    except Exception as e:
        raise Exception(f"Failed to generate ECDH key pair: {str(e)}")


def serialize_public_key(public_key: ec.EllipticCurvePublicKey) -> bytes:
    """
    Serialize public key to PEM format for transmission/storage.
    
    Args:
        public_key: EllipticCurvePublicKey object
        
    Returns:
        bytes: PEM-encoded public key
        
    Raises:
        ValueError: If public key is invalid
    """
    try:
        return public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        )
    except Exception as e:
        raise ValueError(f"Failed to serialize public key: {str(e)}")


def serialize_private_key(private_key: ec.EllipticCurvePrivateKey, password: bytes = None) -> bytes:
    """
    Serialize private key to PEM format (optionally encrypted).
    
    Args:
        private_key: EllipticCurvePrivateKey object
        password: Optional bytes password for encryption
        
    Returns:
        bytes: PEM-encoded private key
        
    Raises:
        ValueError: If private key is invalid
    """
    try:
        encryption = serialization.NoEncryption()
        if password:
            encryption = serialization.BestAvailableEncryption(password)
            
        return private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=encryption
        )
    except Exception as e:
        raise ValueError(f"Failed to serialize private key: {str(e)}")


def load_public_key(pem_data: bytes) -> ec.EllipticCurvePublicKey:
    """
    Load public key from PEM format.
    
    Args:
        pem_data: PEM-encoded public key bytes
        
    Returns:
        EllipticCurvePublicKey object
        
    Raises:
        ValueError: If key loading fails
    """
    try:
        return serialization.load_pem_public_key(
            pem_data,
            backend=default_backend()
        )
    except Exception as e:
        raise ValueError(f"Failed to load public key: {str(e)}")


def load_private_key(pem_data: bytes, password: bytes = None) -> ec.EllipticCurvePrivateKey:
    """
    Load private key from PEM format (encrypted or plain).
    
    Args:
        pem_data: PEM-encoded private key bytes
        password: Optional bytes password for decryption
        
    Returns:
        EllipticCurvePrivateKey object
        
    Raises:
        ValueError: If key loading fails
    """
    try:
        return serialization.load_pem_private_key(
            pem_data,
            password=password,
            backend=default_backend()
        )
    except Exception as e:
        raise ValueError(f"Failed to load private key: {str(e)}")


def derive_shared_secret(
    private_key: ec.EllipticCurvePrivateKey,
    peer_public_key: ec.EllipticCurvePublicKey,
    salt: bytes = None,
    info: bytes = b""
) -> bytes:
    """
    Derive shared secret using ECDH and KDF expansion with HKDF-SHA256.
    
    ECDH Flow Steps 2-3: Exchange public keys and derive shared secret.
    This function performs the key agreement and derives a 32-byte key suitable
    for cryptographic operations (AES, etc.).
    
    Args:
        private_key: Our ECDH private key
        peer_public_key: Peer's ECDH public key
        salt: Optional salt for HKDF (increases entropy)
        info: Optional context info for HKDF
        
    Returns:
        bytes: 32-byte derived key
        
    Raises:
        Exception: If key derivation fails
    """
    try:
        # Step 2: Perform ECDH key agreement
        shared_secret = private_key.exchange(
            ec.ECDH(),
            peer_public_key
        )
        
        # Step 3: Derive final key using HKDF with SHA256
        hkdf = HKDF(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            info=info,
            backend=default_backend()
        )
        
        derived_key = hkdf.derive(shared_secret)
        return derived_key
        
    except Exception as e:
        raise Exception(f"Failed to derive shared secret: {str(e)}")


# ==============================================================================
# AES-256 KEY DERIVATION FROM SHARED SECRET
# ==============================================================================

def derive_aes_session_key(shared_secret: bytes, context: bytes = b"file-encryption") -> bytes:
    """
    Derive an AES-256 session key from the ECDH shared secret using HKDF-SHA256.
    
    WHY NOT USE RAW SHARED SECRET?
    - Raw ECDH output may have biased bits
    - HKDF ensures uniform key distribution
    - Domain separation via context prevents key reuse attacks
    
    Args:
        shared_secret: Raw ECDH shared secret bytes (from SessionKey)
        context: Domain separation context (default: "file-encryption")
        
    Returns:
        bytes: 32-byte (256-bit) AES key suitable for AES-GCM
        
    Raises:
        ValueError: If shared secret is invalid or too short
        
    Example:
        >>> shared_secret = base64.b64decode(session_key.shared_secret)
        >>> aes_key = derive_aes_session_key(shared_secret)
        >>> # aes_key is now ready for encrypt_file()
    """
    if not shared_secret or len(shared_secret) < 16:
        raise ValueError("Shared secret must be at least 16 bytes")
    
    try:
        # HKDF with SHA-256 for key derivation
        # Using fixed salt for deterministic derivation (both parties derive same key)
        hkdf = HKDF(
            algorithm=hashes.SHA256(),
            length=AES_KEY_SIZE,  # 32 bytes = 256 bits
            salt=b"secure-file-transfer-aes-salt",  # Fixed salt for reproducibility
            info=context,  # Domain separation
            backend=default_backend()
        )
        
        aes_key = hkdf.derive(shared_secret)
        return aes_key
        
    except Exception as e:
        raise ValueError(f"Failed to derive AES session key: {str(e)}")


# ==============================================================================
# AES-256-GCM AUTHENTICATED ENCRYPTION
# ==============================================================================

def encrypt_file(file_bytes: bytes, aes_key: bytes) -> tuple:
    """
    Encrypt file bytes using AES-256-GCM authenticated encryption.
    
    AES-GCM FLOW:
    1. Generate random 12-byte IV (nonce) using secure random
    2. Create AESGCM cipher with 256-bit key
    3. Encrypt plaintext → ciphertext || tag (GCM appends tag)
    4. Return ciphertext, IV, and tag separately for storage
    
    SECURITY PROPERTIES:
    - Confidentiality: AES-256 encryption
    - Integrity: 128-bit authentication tag
    - Authenticity: Any tampering detected on decryption
    - IV uniqueness: Random IV ensures ciphertext varies
    
    Args:
        file_bytes: Raw file content to encrypt
        aes_key: 32-byte (256-bit) AES key from derive_aes_session_key()
        
    Returns:
        tuple: (ciphertext: bytes, iv: bytes, tag: bytes)
            - ciphertext: Encrypted file data (same length as input)
            - iv: 12-byte initialization vector (store with ciphertext)
            - tag: 16-byte authentication tag (store with ciphertext)
            
    Raises:
        ValueError: If key size is invalid
        Exception: If encryption fails
        
    Example:
        >>> ciphertext, iv, tag = encrypt_file(file_bytes, aes_key)
        >>> # Store: ciphertext in file, iv & tag in database
    """
    # Validate key size
    if len(aes_key) != AES_KEY_SIZE:
        raise ValueError(f"AES key must be {AES_KEY_SIZE} bytes, got {len(aes_key)}")
    
    if not file_bytes:
        raise ValueError("Cannot encrypt empty file")
    
    try:
        # Step 1: Generate cryptographically secure random IV
        # CRITICAL: Never reuse IV with the same key!
        iv = os.urandom(AES_IV_SIZE)  # 12 bytes = 96 bits
        
        # Step 2: Create AES-GCM cipher
        aesgcm = AESGCM(aes_key)
        
        # Step 3: Encrypt (GCM mode appends 16-byte tag to ciphertext)
        # ciphertext_with_tag = ciphertext + tag
        ciphertext_with_tag = aesgcm.encrypt(iv, file_bytes, associated_data=None)
        
        # Step 4: Separate ciphertext and tag for storage
        # GCM appends 16-byte tag at the end
        ciphertext = ciphertext_with_tag[:-AES_TAG_SIZE]
        tag = ciphertext_with_tag[-AES_TAG_SIZE:]
        
        return ciphertext, iv, tag
        
    except Exception as e:
        raise Exception(f"File encryption failed: {str(e)}")


def decrypt_file(ciphertext: bytes, aes_key: bytes, iv: bytes, tag: bytes) -> bytes:
    """
    Decrypt file bytes using AES-256-GCM authenticated decryption.
    
    AES-GCM DECRYPTION FLOW:
    1. Validate all inputs
    2. Reconstruct ciphertext || tag format
    3. Decrypt and verify authentication tag
    4. Return original plaintext if tag is valid
    
    SECURITY NOTES:
    - If tag verification fails, decryption raises InvalidTag exception
    - This means the ciphertext was tampered with or wrong key used
    - Never expose decryption errors in detail (prevents oracle attacks)
    
    Args:
        ciphertext: Encrypted file data from encrypt_file()
        aes_key: 32-byte AES key (same key used for encryption)
        iv: 12-byte initialization vector from encrypt_file()
        tag: 16-byte authentication tag from encrypt_file()
        
    Returns:
        bytes: Decrypted file content (original plaintext)
        
    Raises:
        ValueError: If parameters are invalid
        cryptography.exceptions.InvalidTag: If authentication fails (tampering detected)
        Exception: If decryption fails
        
    Example:
        >>> plaintext = decrypt_file(ciphertext, aes_key, iv, tag)
        >>> # plaintext is now the original file bytes
    """
    # Validate inputs
    if len(aes_key) != AES_KEY_SIZE:
        raise ValueError(f"AES key must be {AES_KEY_SIZE} bytes, got {len(aes_key)}")
    
    if len(iv) != AES_IV_SIZE:
        raise ValueError(f"IV must be {AES_IV_SIZE} bytes, got {len(iv)}")
    
    if len(tag) != AES_TAG_SIZE:
        raise ValueError(f"Tag must be {AES_TAG_SIZE} bytes, got {len(tag)}")
    
    if not ciphertext:
        raise ValueError("Ciphertext cannot be empty")
    
    try:
        # Step 1: Create AES-GCM cipher
        aesgcm = AESGCM(aes_key)
        
        # Step 2: Reconstruct ciphertext || tag format for decryption
        ciphertext_with_tag = ciphertext + tag
        
        # Step 3: Decrypt and verify tag
        # If tag is invalid, this raises InvalidTag exception
        plaintext = aesgcm.decrypt(iv, ciphertext_with_tag, associated_data=None)
        
        return plaintext
        
    except Exception as e:
        # Don't expose detailed error messages (oracle attack prevention)
        raise Exception("Decryption failed: Invalid key, IV, or corrupted data")