from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.hazmat.backends import default_backend

"""
Production-ready ECDH utility functions using Python cryptography library.

This module provides ECDH (Elliptic Curve Diffie-Hellman) key exchange utilities
with key serialization and shared secret derivation using HKDF.
"""



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