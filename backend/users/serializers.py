"""
User serializers for API request/response handling.
Handles validation, authentication, and data transformation.
"""

from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from django.contrib.auth.password_validation import validate_password
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta

# Import ECDH utilities for key generation during registration
from crypto.utils import generate_key_pair, serialize_public_key, serialize_private_key

User = get_user_model()

# A user is "online" if their last heartbeat was within this window.
# Must match ONLINE_THRESHOLD_SECONDS in views_users.py.
ONLINE_THRESHOLD_SECONDS = 60


class UserSerializer(serializers.ModelSerializer):
    """
    Serializer for User model - used for user listing and profile display.
    
    Key design choice — is_online is a computed field:
    Rather than trusting the stored boolean (which can be stale when a browser
    tab is closed without sending a logout), we recompute online status at
    serialisation time using last_seen.  A user is online iff:
        last_seen >= now() - ONLINE_THRESHOLD_SECONDS (60 s)
    
    Example Response:
    {
        "id": 1,
        "username": "john_doe",
        "email": "john@example.com",
        "first_name": "John",
        "last_name": "Doe",
        "is_online": true,          ← dynamically computed
        "last_seen": "2026-03-13T10:30:00Z",
        "last_activity": "2026-03-13T10:30:00Z",
        "created_at": "2026-01-15T08:00:00Z"
    }
    """
    
    # is_online is computed from last_seen at serialisation time.
    # This prevents the "ghost online" bug: if a user closes the browser
    # without logging out, they will automatically appear offline once
    # ONLINE_THRESHOLD_SECONDS have passed with no heartbeat.
    is_online = serializers.SerializerMethodField()

    def get_is_online(self, obj) -> bool:
        """
        Return True only if the user sent a heartbeat within the last 60 s.
        Falls back to False if last_seen is None (user never sent a heartbeat).
        """
        if not obj.last_seen:
            return False
        threshold = timezone.now() - timedelta(seconds=ONLINE_THRESHOLD_SECONDS)
        return obj.last_seen >= threshold
    
    class Meta:
        model = User
        fields = [
            'id', 
            'username', 
            'email', 
            'first_name', 
            'last_name',
            'is_online',       # computed — see get_is_online()
            'last_seen',       # raw heartbeat timestamp (for frontend debugging)
            'last_activity',
            'created_at',
        ]
        read_only_fields = ['id', 'created_at', 'last_activity', 'last_seen']


class UserRegistrationSerializer(serializers.ModelSerializer):
    """
    Serializer for user registration with password validation.
    
    Frontend mock replacement:
    - Replaces mock registration logic in AuthPage.tsx
    - Provides real user creation with validation
    
    Request Example:
    {
        "username": "john_doe",
        "email": "john@example.com",
        "password": "SecurePass123!",
        "password_confirm": "SecurePass123!",
        "first_name": "John",
        "last_name": "Doe"
    }
    
    Response Example:
    {
        "id": 1,
        "username": "john_doe",
        "email": "john@example.com",
        "first_name": "John",
        "last_name": "Doe",
        "message": "User registered successfully"
    }
    """
    
    password = serializers.CharField(
        write_only=True,
        required=True,
        validators=[validate_password],
        style={'input_type': 'password'}
    )
    password_confirm = serializers.CharField(
        write_only=True,
        required=True,
        style={'input_type': 'password'}
    )
    
    class Meta:
        model = User
        fields = [
            'id',
            'username',
            'email',
            'password',
            'password_confirm',
            'first_name',
            'last_name',
        ]
        extra_kwargs = {
            'first_name': {'required': False},
            'last_name': {'required': False},
        }
    
    def validate_email(self, value):
        """Ensure email is unique."""
        if User.objects.filter(email=value.lower()).exists():
            raise serializers.ValidationError("A user with this email already exists.")
        return value.lower()
    
    def validate_username(self, value):
        """Ensure username is unique and valid."""
        if User.objects.filter(username=value.lower()).exists():
            raise serializers.ValidationError("A user with this username already exists.")
        return value.lower()
    
    def validate(self, attrs):
        """Validate password confirmation matches."""
        if attrs['password'] != attrs['password_confirm']:
            raise serializers.ValidationError({
                "password_confirm": "Passwords do not match."
            })
        return attrs
    
    def create(self, validated_data):
        """
        Create user with hashed password and generate ECDH key pair.
        
        ECDH Key Generation Flow:
        1. Create the Django User with hashed password
        2. Generate ECDH key pair (SECP256R1 curve)
        3. Serialize public key to PEM format
        4. Serialize private key to PEM format
        5. Store public key in UserProfile
        6. Encrypt and store private key in UserPrivateKey
        
        Security:
        - Password is hashed using Django's default hasher (PBKDF2)
        - Private key is encrypted using Fernet before storage
        - Private key is NEVER returned in API response
        """
        from users.models import UserProfile, UserPrivateKey
        
        validated_data.pop('password_confirm')
        
        # Step 1: Create user with hashed password
        user = User.objects.create_user(
            username=validated_data['username'],
            email=validated_data['email'],
            password=validated_data['password'],
            first_name=validated_data.get('first_name', ''),
            last_name=validated_data.get('last_name', ''),
        )
        
        try:
            # Step 2: Generate ECDH key pair using SECP256R1 (P-256) curve
            private_key, public_key = generate_key_pair()
            
            # Step 3: Serialize public key to PEM format (for sharing)
            public_key_pem = serialize_public_key(public_key)
            
            # Step 4: Serialize private key to PEM format (raw bytes)
            private_key_pem = serialize_private_key(private_key)
            
            # Step 5: Create UserProfile and store public key
            UserProfile.objects.create(
                user=user,
                public_key=public_key_pem.decode('utf-8'),
                key_created_at=timezone.now()
            )
            
            # Step 6: Encrypt and store private key securely
            encrypted_private_key = UserPrivateKey.encrypt_private_key(private_key_pem)
            UserPrivateKey.objects.create(
                user=user,
                encrypted_private_key=encrypted_private_key
            )
            
        except Exception as e:
            # If key generation fails, delete the user to maintain consistency
            user.delete()
            raise serializers.ValidationError(
                f"Failed to generate encryption keys: {str(e)}"
            )
        
        return user


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    """
    Custom JWT token serializer with additional user data in response.
    
    Frontend mock replacement:
    - Replaces mock login logic in AuthPage.tsx
    - Provides real JWT tokens for authentication
    
    Response Example:
    {
        "access": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
        "refresh": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
        "user": {
            "id": 1,
            "username": "john_doe",
            "email": "john@example.com",
            "first_name": "John",
            "last_name": "Doe"
        }
    }
    """
    
    def validate(self, attrs):
        data = super().validate(attrs)
        
        # Add user information to response
        user = self.user
        user.set_online(True)  # Mark user as online on login
        
        data['user'] = {
            'id': user.id,
            'username': user.username,
            'email': user.email,
            'first_name': user.first_name,
            'last_name': user.last_name,
            'is_online': user.is_online,
        }
        
        return data


class UserProfileSerializer(serializers.ModelSerializer):
    """
    Serializer for user profile updates.
    
    Request Example:
    {
        "first_name": "John",
        "last_name": "Doe",
        "public_key": "-----BEGIN PUBLIC KEY-----..."
    }
    """
    
    class Meta:
        model = User
        fields = [
            'id',
            'username',
            'email',
            'first_name',
            'last_name',
            'public_key',
            'is_online',
            'last_activity',
            'created_at',
        ]
        read_only_fields = ['id', 'username', 'email', 'created_at', 'last_activity']


class PasswordChangeSerializer(serializers.Serializer):
    """
    Serializer for password change.
    
    Request Example:
    {
        "old_password": "OldPass123!",
        "new_password": "NewPass456!",
        "new_password_confirm": "NewPass456!"
    }
    """
    
    old_password = serializers.CharField(
        required=True,
        style={'input_type': 'password'}
    )
    new_password = serializers.CharField(
        required=True,
        validators=[validate_password],
        style={'input_type': 'password'}
    )
    new_password_confirm = serializers.CharField(
        required=True,
        style={'input_type': 'password'}
    )
    
    def validate(self, attrs):
        if attrs['new_password'] != attrs['new_password_confirm']:
            raise serializers.ValidationError({
                "new_password_confirm": "New passwords do not match."
            })
        return attrs
