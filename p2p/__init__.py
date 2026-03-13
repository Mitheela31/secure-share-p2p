"""
Secure P2P File Transfer Package.

A LAN-based peer-to-peer secure file sharing system with:
- UDP broadcast discovery
- TCP secure connection
- ECDH key exchange
- AES-256-GCM encryption

Modules:
    discovery: UDP broadcast and listen for device discovery
    connection: TCP server/client with handshake verification
    crypto_utils: ECDH, HKDF, and AES-GCM implementations
    file_transfer: Encrypted file send/receive

Usage:
    # As sender
    from p2p.main_sender import SenderApplication
    app = SenderApplication()
    app.run()
    
    # As receiver
    from p2p.main_receiver import ReceiverApplication
    app = ReceiverApplication()
    app.run()
"""

__version__ = "1.0.0"
__author__ = "Secure P2P Team"

from .discovery import UDPBroadcaster, UDPListener
from .connection import TCPServer, TCPClient
from .crypto_utils import (
    SecureKeyExchange,
    generate_key_pair,
    encrypt_data,
    decrypt_data,
)
from .file_transfer import (
    FileSender,
    FileReceiver,
    send_file_to_receiver,
    receive_file_from_sender,
)

__all__ = [
    # Discovery
    "UDPBroadcaster",
    "UDPListener",
    
    # Connection
    "TCPServer",
    "TCPClient",
    
    # Crypto
    "SecureKeyExchange",
    "generate_key_pair",
    "encrypt_data",
    "decrypt_data",
    
    # File Transfer
    "FileSender",
    "FileReceiver",
    "send_file_to_receiver",
    "receive_file_from_sender",
]
