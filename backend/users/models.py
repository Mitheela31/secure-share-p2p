"""
User models for Secure File Transfer Application.
Custom user model with extended profile fields.

This model replaces frontend mock data for:
- User authentication state
- User profile information
- User listing in transfer recipient selection
"""

from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils import timezone
from django.conf import settings
from cryptography.fernet import Fernet
import base64
import hashlib
import uuid


class User(AbstractUser):
    """
    Custom User model extending Django's AbstractUser.
    
    Frontend mock replacement:
    - Replaces any hardcoded user data in AuthPage.tsx
    - Replaces user lists in SenderDashboard.tsx recipient selection
    - Provides real user data for TransferHistory.tsx
    
    API Response Example:
    {
        "id": 1,
        "username": "john_doe",
        "email": "john@example.com",
        "first_name": "John",
        "last_name": "Doe",
        "is_online": true,
        "last_activity": "2026-02-06T10:30:00Z",
        "created_at": "2026-01-15T08:00:00Z"
    }
    """
    
    id = models.AutoField(primary_key=True)
    email = models.EmailField(unique=True, help_text="User's email address")
    
    # Extended profile fields
    is_online = models.BooleanField(
        default=False, 
        help_text="Whether user is currently online (legacy flag — use last_seen for accuracy)"
    )
    last_activity = models.DateTimeField(
        null=True, 
        blank=True,
        help_text="Last activity timestamp"
    )

    # -------------------------------------------------------------------------
    # PHASE 8 FIX: last_seen — heartbeat-based presence detection
    # -------------------------------------------------------------------------
    # Unlike `is_online` (a boolean that can get stuck), `last_seen` is a
    # timestamp set every time the frontend sends a heartbeat POST.
    # A user is considered "online" only if:
    #   last_seen >= now() - ONLINE_THRESHOLD_SECONDS (60 seconds)
    # This automatically expires once no heartbeat is received, avoiding the
    # "ghost online" bug where closed browsers still appear active.
    # -------------------------------------------------------------------------
    last_seen = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Last heartbeat timestamp — used to compute real-time online status"
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text="Account creation timestamp"
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        help_text="Last profile update timestamp"
    )
    
    class Meta:
        db_table = 'users'
        ordering = ['-created_at']
        verbose_name = 'User'
        verbose_name_plural = 'Users'
    
    def __str__(self):
        return f"{self.username} ({self.email})"
    
    def update_activity(self):
        """Update last activity timestamp."""
        self.last_activity = timezone.now()
        self.save(update_fields=['last_activity'])
    
    def update_last_seen(self):
        """
        Record a fresh heartbeat timestamp.

        Called by the /users/heartbeat/ endpoint every ~30 s.
        The `is_online` computed property (see UserSerializer) evaluates
        this value at query time so no boolean flag can become stale.
        """
        now = timezone.now()
        self.last_seen = now
        self.last_activity = now
        self.is_online = True   # kept in sync for legacy queries
        self.save(update_fields=['last_seen', 'last_activity', 'is_online'])

    def set_online(self, online_status=True):
        """Set user online status (legacy — prefer update_last_seen for heartbeats)."""
        self.is_online = online_status
        self.last_activity = timezone.now()
        if online_status:
            self.last_seen = timezone.now()
        self.save(update_fields=['is_online', 'last_activity', 'last_seen'])


class UserProfile(models.Model):
    """
    User Profile model (extends Django User).
    
    Stores additional user information including public key for encryption.
    OneToOne relationship with the custom User model.
    """

    user = models.OneToOneField(
        'User',
        on_delete=models.CASCADE,
        related_name='profile',
        help_text="Associated user account"
    )
    public_key = models.TextField(
        blank=True,
        null=True,
        help_text="User's public key for end-to-end encryption (ECDH)"
    )
    key_created_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When the public key was created"
    )

    class Meta:
        db_table = 'user_profiles'
        verbose_name = 'User Profile'
        verbose_name_plural = 'User Profiles'

    def __str__(self):
        return f"Profile for {self.user.username}"

    def set_public_key(self, key):
        """Set the user's public key and update timestamp."""
        self.public_key = key
        self.key_created_at = timezone.now()
        self.save(update_fields=['public_key', 'key_created_at'])


class UserPrivateKey(models.Model):
    """
    Secure storage for user's ECDH private key.
    
    The private key is encrypted using Fernet symmetric encryption
    derived from Django's SECRET_KEY. This ensures:
    - Private keys are never stored in plaintext
    - Keys are only accessible server-side
    - Database compromise doesn't expose raw private keys
    
    SECURITY NOTES:
    - Never expose encrypted_private_key in API responses
    - Only decrypt when performing ECDH key exchange
    - Consider using HSM or vault in production
    """
    
    user = models.OneToOneField(
        'User',
        on_delete=models.CASCADE,
        related_name='private_key_storage',
        help_text="Associated user account"
    )
    encrypted_private_key = models.TextField(
        help_text="Fernet-encrypted ECDH private key (PEM format)"
    )
    key_id = models.UUIDField(
        default=uuid.uuid4,
        editable=False,
        help_text="Unique identifier for key rotation tracking"
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text="When the private key was created"
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        help_text="When the private key was last updated"
    )
    
    class Meta:
        db_table = 'user_private_keys'
        verbose_name = 'User Private Key'
        verbose_name_plural = 'User Private Keys'
    
    def __str__(self):
        return f"Private Key for {self.user.username} (ID: {self.key_id})"
    
    @staticmethod
    def _get_encryption_key():
        """
        Derive a Fernet-compatible encryption key from Django's SECRET_KEY.
        
        Uses SHA-256 to create a 32-byte key, then base64 encode for Fernet.
        This ensures consistent key derivation across the application.
        """
        # Use Django's SECRET_KEY as the basis for encryption
        secret = settings.SECRET_KEY.encode('utf-8')
        # Derive a 32-byte key using SHA-256
        key_bytes = hashlib.sha256(secret).digest()
        # Fernet requires base64-encoded 32-byte key
        return base64.urlsafe_b64encode(key_bytes)
    
    @classmethod
    def encrypt_private_key(cls, private_key_pem: bytes) -> str:
        """
        Encrypt a PEM-encoded private key for secure storage.
        
        Args:
            private_key_pem: Raw PEM bytes of the ECDH private key
            
        Returns:
            str: Base64-encoded encrypted private key
        """
        fernet = Fernet(cls._get_encryption_key())
        encrypted = fernet.encrypt(private_key_pem)
        return encrypted.decode('utf-8')
    
    @classmethod
    def decrypt_private_key(cls, encrypted_key: str) -> bytes:
        """
        Decrypt an encrypted private key for ECDH operations.
        
        Args:
            encrypted_key: Base64-encoded encrypted private key
            
        Returns:
            bytes: Raw PEM bytes of the ECDH private key
            
        Raises:
            InvalidToken: If decryption fails (wrong key or corrupted data)
        """
        fernet = Fernet(cls._get_encryption_key())
        return fernet.decrypt(encrypted_key.encode('utf-8'))
    
    def get_decrypted_private_key(self) -> bytes:
        """
        Get the decrypted private key PEM bytes for this user.
        
        Returns:
            bytes: Raw PEM bytes of the ECDH private key
        """
        return self.decrypt_private_key(self.encrypted_private_key)


