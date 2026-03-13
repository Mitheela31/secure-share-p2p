"""
URL configuration for crypto app.

Provides endpoints for ECDH key exchange operations:
- Public key retrieval
- Key exchange initiation
- Session key management

All endpoints require authentication except where noted.
"""

from django.urls import path
from .views import (
    PublicKeyView,
    MyPublicKeyView,
    InitiateKeyExchangeView,
    SessionKeyDetailView,
    RetrieveSharedSecretView,
    ListSessionKeysView,
    DeleteSessionKeyView,
    VerifyKeyPairView,
)

app_name = 'crypto'

urlpatterns = [
    # Public key endpoints
    # GET /api/crypto/public-key/<user_id>/ - Fetch user's public key
    path('public-key/<int:user_id>/', PublicKeyView.as_view(), name='public-key'),
    
    # GET /api/crypto/my-public-key/ - Fetch own public key
    path('my-public-key/', MyPublicKeyView.as_view(), name='my-public-key'),
    
    # Key exchange endpoints
    # POST /api/crypto/key-exchange/initiate/ - Initiate ECDH key exchange
    path('key-exchange/initiate/', InitiateKeyExchangeView.as_view(), name='initiate-key-exchange'),
    
    # Session management endpoints
    # GET /api/crypto/sessions/ - List all user's sessions
    path('sessions/', ListSessionKeysView.as_view(), name='session-list'),
    
    # GET /api/crypto/session/<id>/ - Get session details (no secret)
    path('session/<int:session_id>/', SessionKeyDetailView.as_view(), name='session-detail'),
    
    # GET /api/crypto/session/<id>/secret/ - Retrieve shared secret
    path('session/<int:session_id>/secret/', RetrieveSharedSecretView.as_view(), name='session-secret'),
    
    # DELETE /api/crypto/session/<id>/ - Delete/revoke session
    path('session/<int:session_id>/delete/', DeleteSessionKeyView.as_view(), name='session-delete'),
    
    # Key verification endpoint
    # GET /api/crypto/verify-keys/ - Verify user's key pair is valid
    path('verify-keys/', VerifyKeyPairView.as_view(), name='verify-keys'),
]
