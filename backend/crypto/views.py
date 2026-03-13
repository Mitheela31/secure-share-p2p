"""
Crypto Views for ECDH Key Exchange API.

This module provides API endpoints for:
1. Fetching user public keys
2. Initiating ECDH key exchange
3. Deriving and storing shared secrets

ECDH (Elliptic Curve Diffie-Hellman) Flow:
1. Both parties have key pairs (generated at registration)
2. Sender fetches receiver's public key
3. Sender initiates key exchange:
   - Load sender's private key (decrypted from storage)
   - Load receiver's public key
   - Derive shared secret using ECDH
   - Store encrypted shared secret in SessionKey model
4. Both parties now share a secret for symmetric encryption

Security Considerations:
- Private keys are NEVER exposed in API responses
- Shared secrets are base64 encoded before storage
- All endpoints require authentication
- Proper error handling without leaking sensitive info
"""

import base64
import logging
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404

from .models import SessionKey
from .utils import (
    load_public_key,
    load_private_key,
    derive_shared_secret
)
from users.models import UserProfile, UserPrivateKey

User = get_user_model()
logger = logging.getLogger(__name__)


class PublicKeyView(APIView):
    """
    API endpoint to fetch a user's public key.
    
    GET /api/crypto/public-key/<user_id>/
    
    This is the first step in ECDH key exchange:
    - Sender requests receiver's public key
    - Public key is safe to transmit over network
    - Anyone can see public keys without compromising security
    
    Response:
    {
        "user_id": 2,
        "username": "receiver_user",
        "public_key": "-----BEGIN PUBLIC KEY-----\n..."
    }
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request, user_id):
        """Fetch public key for a specific user."""
        try:
            # Get the target user
            target_user = get_object_or_404(User, id=user_id)
            
            # Get their profile with public key
            try:
                profile = UserProfile.objects.get(user=target_user)
            except UserProfile.DoesNotExist:
                return Response({
                    'status': 'error',
                    'message': 'User has not completed key setup.'
                }, status=status.HTTP_404_NOT_FOUND)
            
            # Verify public key exists
            if not profile.public_key:
                return Response({
                    'status': 'error',
                    'message': 'User public key not available.'
                }, status=status.HTTP_404_NOT_FOUND)
            
            return Response({
                'status': 'success',
                'data': {
                    'user_id': target_user.id,
                    'username': target_user.username,
                    'public_key': profile.public_key,
                    'key_created_at': profile.key_created_at
                }
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"Error fetching public key for user {user_id}: {str(e)}")
            return Response({
                'status': 'error',
                'message': 'Failed to fetch public key.'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class MyPublicKeyView(APIView):
    """
    API endpoint to fetch the authenticated user's own public key.
    
    GET /api/crypto/my-public-key/
    
    Useful for:
    - Verifying key generation was successful
    - Displaying public key in UI for manual sharing
    - Key management interfaces
    
    Note: Private key is NEVER returned.
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """Fetch the current user's public key."""
        try:
            profile = UserProfile.objects.get(user=request.user)
            
            if not profile.public_key:
                return Response({
                    'status': 'error',
                    'message': 'Your encryption keys have not been generated.'
                }, status=status.HTTP_404_NOT_FOUND)
            
            return Response({
                'status': 'success',
                'data': {
                    'user_id': request.user.id,
                    'username': request.user.username,
                    'public_key': profile.public_key,
                    'key_created_at': profile.key_created_at
                }
            }, status=status.HTTP_200_OK)
            
        except UserProfile.DoesNotExist:
            return Response({
                'status': 'error',
                'message': 'User profile not found. Please contact support.'
            }, status=status.HTTP_404_NOT_FOUND)


class InitiateKeyExchangeView(APIView):
    """
    API endpoint to initiate ECDH key exchange with another user.
    
    POST /api/crypto/key-exchange/initiate/
    
    Request Body:
    {
        "receiver_id": 123
    }
    
    ECDH Key Exchange Flow:
    1. Validate receiver exists and has public key
    2. Load sender's encrypted private key from storage
    3. Decrypt sender's private key
    4. Load receiver's public key
    5. Perform ECDH key agreement:
       shared_secret = sender_private_key.exchange(receiver_public_key)
    6. Derive final key using HKDF-SHA256
    7. Store base64-encoded shared secret in SessionKey model
    
    Response:
    {
        "status": "success",
        "message": "Key exchange completed successfully",
        "data": {
            "session_id": 1,
            "receiver_id": 123,
            "receiver_username": "bob",
            "created_at": "2026-02-20T10:30:00Z"
        }
    }
    
    Security Notes:
    - Private key is decrypted only in memory, never exposed
    - Shared secret is encoded before storage
    - Both parties derive the SAME shared secret
    """
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        """Initiate ECDH key exchange with a receiver."""
        receiver_id = request.data.get('receiver_id')
        
        # Validate receiver_id is provided
        if not receiver_id:
            return Response({
                'status': 'error',
                'message': 'receiver_id is required.'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Cannot exchange keys with yourself
        if int(receiver_id) == request.user.id:
            return Response({
                'status': 'error',
                'message': 'Cannot initiate key exchange with yourself.'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            # Step 1: Get receiver and validate they have a public key
            receiver = get_object_or_404(User, id=receiver_id)
            
            try:
                receiver_profile = UserProfile.objects.get(user=receiver)
            except UserProfile.DoesNotExist:
                return Response({
                    'status': 'error',
                    'message': 'Receiver has not completed key setup.'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            if not receiver_profile.public_key:
                return Response({
                    'status': 'error',
                    'message': 'Receiver public key not available.'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Step 2: Get sender's encrypted private key
            try:
                sender_private_key_storage = UserPrivateKey.objects.get(user=request.user)
            except UserPrivateKey.DoesNotExist:
                return Response({
                    'status': 'error',
                    'message': 'Your private key is not available. Please re-register.'
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            
            # Step 3: Decrypt sender's private key (in memory only)
            try:
                sender_private_key_pem = sender_private_key_storage.get_decrypted_private_key()
            except Exception as e:
                logger.error(f"Failed to decrypt private key for user {request.user.id}: {str(e)}")
                return Response({
                    'status': 'error',
                    'message': 'Failed to load your encryption key.'
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            
            # Step 4: Load keys as cryptographic objects
            try:
                # Load sender's private key from PEM bytes
                sender_private_key = load_private_key(sender_private_key_pem)
                
                # Load receiver's public key from PEM string
                receiver_public_key = load_public_key(
                    receiver_profile.public_key.encode('utf-8')
                )
            except Exception as e:
                logger.error(f"Failed to load keys: {str(e)}")
                return Response({
                    'status': 'error',
                    'message': 'Failed to process encryption keys.'
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            
            # Step 5: Perform ECDH key exchange to derive shared secret
            # Both parties will derive the SAME 32-byte secret:
            # - Sender uses: sender_private + receiver_public
            # - Receiver uses: receiver_private + sender_public
            try:
                # Derive shared secret with context info for domain separation
                shared_secret = derive_shared_secret(
                    private_key=sender_private_key,
                    peer_public_key=receiver_public_key,
                    salt=None,  # Optional: Add deterministic salt for extra security
                    info=f"secure-file-transfer:{request.user.id}:{receiver.id}".encode('utf-8')
                )
            except Exception as e:
                logger.error(f"ECDH key exchange failed: {str(e)}")
                return Response({
                    'status': 'error',
                    'message': 'Key exchange computation failed.'
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            
            # Step 6: Encode shared secret for storage
            shared_secret_b64 = base64.b64encode(shared_secret).decode('utf-8')
            
            # Step 7: Store or update SessionKey
            # First, revoke any existing active session between these users
            SessionKey.objects.filter(
                sender=request.user,
                receiver=receiver,
                is_active=True
            ).update(is_active=False)
            
            # Create new session
            session_key = SessionKey.objects.create(
                sender=request.user,
                receiver=receiver,
                shared_secret=shared_secret_b64,
                is_active=True
            )
            
            return Response({
                'status': 'success',
                'message': 'Key exchange completed successfully.',
                'data': {
                    'session_id': session_key.id,
                    'receiver_id': receiver.id,
                    'receiver_username': receiver.username,
                    'created_at': session_key.created_at.isoformat(),
                    'expires_at': session_key.expires_at.isoformat()
                }
            }, status=status.HTTP_201_CREATED)
            
        except User.DoesNotExist:
            return Response({
                'status': 'error',
                'message': 'Receiver user not found.'
            }, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error(f"Key exchange error: {str(e)}")
            return Response({
                'status': 'error',
                'message': 'An unexpected error occurred during key exchange.'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class SessionKeyDetailView(APIView):
    """
    API endpoint to retrieve session key details (NOT the secret itself).
    
    GET /api/crypto/session/<session_id>/
    
    Used to verify a session exists and check its status.
    The shared secret is NOT exposed in this endpoint for security.
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request, session_id):
        """Get session key details."""
        try:
            session = SessionKey.objects.get(id=session_id)
            
            # Verify the user is part of this session
            if request.user not in [session.sender, session.receiver]:
                return Response({
                    'status': 'error',
                    'message': 'You are not authorized to view this session.'
                }, status=status.HTTP_403_FORBIDDEN)
            
            return Response({
                'status': 'success',
                'data': {
                    'session_id': session.id,
                    'sender_id': session.sender.id,
                    'sender_username': session.sender.username,
                    'receiver_id': session.receiver.id,
                    'receiver_username': session.receiver.username,
                    'is_active': session.is_active,
                    'is_expired': session.is_expired,
                    'is_valid': session.is_valid,
                    'expires_at': session.expires_at.isoformat(),
                    'created_at': session.created_at.isoformat()
                    # NOTE: shared_secret is intentionally NOT included
                }
            }, status=status.HTTP_200_OK)
            
        except SessionKey.DoesNotExist:
            return Response({
                'status': 'error',
                'message': 'Session not found.'
            }, status=status.HTTP_404_NOT_FOUND)


class RetrieveSharedSecretView(APIView):
    """
    API endpoint to retrieve the shared secret for an active session.
    
    GET /api/crypto/session/<session_id>/secret/
    
    SECURITY WARNING:
    This endpoint returns the actual shared secret, which should be
    used ONLY for encrypting/decrypting file data. In a production
    system, consider additional safeguards:
    - Rate limiting
    - Audit logging
    - Short-lived tokens for secret access
    
    The shared secret is returned base64-encoded.
    
    SECURITY: Returns 403 if session is revoked or expired.
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request, session_id):
        """Retrieve the shared secret for a session."""
        try:
            session = SessionKey.objects.get(id=session_id)
            
            # Verify the user is part of this session
            if request.user not in [session.sender, session.receiver]:
                logger.warning(
                    f"Unauthorized secret access attempt: User {request.user.id} "
                    f"tried to access session {session_id}"
                )
                return Response({
                    'status': 'error',
                    'message': 'You are not authorized to access this session.'
                }, status=status.HTTP_403_FORBIDDEN)
            
            # SECURITY: Check if session is valid (active and not expired)
            if not session.is_valid:
                reason = "revoked" if not session.is_active else "expired"
                logger.warning(
                    f"Invalid session secret access: User {request.user.id} "
                    f"tried to access {reason} session {session_id}"
                )
                return Response({
                    'status': 'error',
                    'message': f'Session has been {reason}. Please initiate a new key exchange.'
                }, status=status.HTTP_403_FORBIDDEN)
            
            # Log the access for audit purposes
            logger.info(
                f"Shared secret accessed: User {request.user.id} "
                f"for session {session_id}"
            )
            
            return Response({
                'status': 'success',
                'data': {
                    'session_id': session.id,
                    'shared_secret': session.shared_secret,  # Base64 encoded
                    'expires_at': session.expires_at.isoformat(),
                    'created_at': session.created_at.isoformat()
                }
            }, status=status.HTTP_200_OK)
            
        except SessionKey.DoesNotExist:
            return Response({
                'status': 'error',
                'message': 'Session not found.'
            }, status=status.HTTP_404_NOT_FOUND)


class ListSessionKeysView(APIView):
    """
    API endpoint to list all sessions for the authenticated user.
    
    GET /api/crypto/sessions/
    GET /api/crypto/sessions/?active_only=true
    
    Returns sessions where the user is either sender or receiver.
    Shared secrets are NOT included in the list response.
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """List all sessions for the current user."""
        # Get sessions where user is sender or receiver
        sessions_as_sender = SessionKey.objects.filter(sender=request.user)
        sessions_as_receiver = SessionKey.objects.filter(receiver=request.user)
        
        # Combine and serialize
        sessions = (sessions_as_sender | sessions_as_receiver).order_by('-created_at')
        
        # Optional: Filter to active-only
        active_only = request.query_params.get('active_only', '').lower() == 'true'
        if active_only:
            sessions = sessions.filter(is_active=True)
        
        session_list = []
        for session in sessions:
            session_list.append({
                'session_id': session.id,
                'sender_id': session.sender.id,
                'sender_username': session.sender.username,
                'receiver_id': session.receiver.id,
                'receiver_username': session.receiver.username,
                'is_active': session.is_active,
                'is_expired': session.is_expired,
                'is_valid': session.is_valid,
                'expires_at': session.expires_at.isoformat(),
                'created_at': session.created_at.isoformat(),
                'role': 'sender' if session.sender == request.user else 'receiver'
            })
        
        return Response({
            'status': 'success',
            'data': {
                'count': len(session_list),
                'sessions': session_list
            }
        }, status=status.HTTP_200_OK)


class DeleteSessionKeyView(APIView):
    """
    API endpoint to revoke a session key.
    
    DELETE /api/crypto/session/<session_id>/
    
    Allows either party to revoke a session, invalidating the shared secret.
    Sessions are soft-deleted (is_active=False) to maintain audit trail.
    """
    permission_classes = [IsAuthenticated]
    
    def delete(self, request, session_id):
        """Revoke a session key (soft delete)."""
        try:
            session = SessionKey.objects.get(id=session_id)
            
            # Verify the user is part of this session
            if request.user not in [session.sender, session.receiver]:
                return Response({
                    'status': 'error',
                    'message': 'You are not authorized to revoke this session.'
                }, status=status.HTTP_403_FORBIDDEN)
            
            # Check if already revoked
            if not session.is_active:
                return Response({
                    'status': 'error',
                    'message': 'Session has already been revoked.'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Log the revocation
            logger.info(
                f"Session revoked: User {request.user.id} revoked session {session_id}"
            )
            
            # Soft delete using revoke() method
            session.revoke()
            
            return Response({
                'status': 'success',
                'message': 'Session revoked successfully.'
            }, status=status.HTTP_200_OK)
            
        except SessionKey.DoesNotExist:
            return Response({
                'status': 'error',
                'message': 'Session not found.'
            }, status=status.HTTP_404_NOT_FOUND)


class VerifyKeyPairView(APIView):
    """
    API endpoint to verify that the user's key pair is valid and complete.
    
    GET /api/crypto/verify-keys/
    
    Checks:
    - UserProfile exists with public key
    - UserPrivateKey exists with encrypted private key
    - Keys can be loaded without errors
    
    Does NOT expose any key material.
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """Verify the user's ECDH key pair is valid."""
        issues = []
        
        # Check UserProfile and public key
        try:
            profile = UserProfile.objects.get(user=request.user)
            if not profile.public_key:
                issues.append('Public key is missing')
            else:
                # Try to load the public key to verify it's valid
                try:
                    load_public_key(profile.public_key.encode('utf-8'))
                except Exception:
                    issues.append('Public key is corrupted or invalid')
        except UserProfile.DoesNotExist:
            issues.append('User profile not found')
        
        # Check UserPrivateKey
        try:
            private_key_storage = UserPrivateKey.objects.get(user=request.user)
            # Try to decrypt and load the private key
            try:
                private_key_pem = private_key_storage.get_decrypted_private_key()
                load_private_key(private_key_pem)
            except Exception:
                issues.append('Private key cannot be decrypted or is invalid')
        except UserPrivateKey.DoesNotExist:
            issues.append('Private key not found')
        
        if issues:
            return Response({
                'status': 'error',
                'message': 'Key verification failed',
                'issues': issues
            }, status=status.HTTP_400_BAD_REQUEST)
        
        return Response({
            'status': 'success',
            'message': 'Key pair is valid and complete',
            'data': {
                'public_key_created_at': profile.key_created_at.isoformat() if profile.key_created_at else None,
                'private_key_id': str(private_key_storage.key_id)
            }
        }, status=status.HTTP_200_OK)
