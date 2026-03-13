"""
Encrypted File Transfer Module for Secure P2P Communication.

Architecture:
============
This module handles the secure transfer of files over TCP:

SENDER:
    1. Read file from disk
    2. Encrypt using AES-256-GCM
    3. Send metadata (filename, size)
    4. Send encrypted data (IV + tag + ciphertext)
    
RECEIVER:
    1. Receive metadata
    2. Receive encrypted data
    3. Decrypt using AES-256-GCM
    4. Save to local disk

Transfer Protocol:
=================
The file transfer uses a structured protocol:

1. FILE_METADATA message:
   - Original filename
   - Original file size
   - MIME type (optional)
   
2. FILE_DATA message:
   - IV (12 bytes)
   - Authentication tag (16 bytes)
   - Ciphertext length (4 bytes)
   - Ciphertext (variable)

Security Notes:
===============
- Files are NEVER transmitted in plaintext
- Each file uses a unique IV
- Authentication tag ensures integrity
- Failed decryption indicates tampering
"""

import os
import struct
import json
import logging
import hashlib
from pathlib import Path
from typing import Optional, Callable, Tuple
from dataclasses import dataclass, asdict
import mimetypes

from connection import SecureTCPConnection, TCPServer, TCPClient
from crypto_utils import (
    SecureKeyExchange,
    encrypt_data,
    decrypt_data,
    EncryptedData,
    IV_SIZE,
    TAG_SIZE
)

# Configure logging
logger = logging.getLogger(__name__)

# Protocol constants
MSG_TYPE_KEY_EXCHANGE = b'KEY'
MSG_TYPE_FILE_METADATA = b'META'
MSG_TYPE_FILE_DATA = b'DATA'
MSG_TYPE_TRANSFER_COMPLETE = b'DONE'
MSG_TYPE_ERROR = b'ERR'

# Maximum file size (1GB)
MAX_FILE_SIZE = 1 * 1024 * 1024 * 1024

# Chunk size for large files (1MB)
CHUNK_SIZE = 1 * 1024 * 1024


@dataclass
class FileMetadata:
    """Metadata about a file being transferred."""
    filename: str
    filesize: int
    checksum: str  # SHA-256 hash
    mime_type: str
    
    def to_json(self) -> bytes:
        """Serialize to JSON bytes."""
        return json.dumps(asdict(self)).encode('utf-8')
        
    @classmethod
    def from_json(cls, data: bytes) -> 'FileMetadata':
        """Deserialize from JSON bytes."""
        obj = json.loads(data.decode('utf-8'))
        return cls(**obj)


@dataclass
class TransferProgress:
    """Progress information for file transfer."""
    total_bytes: int
    transferred_bytes: int
    
    @property
    def percentage(self) -> float:
        """Get transfer progress as percentage."""
        if self.total_bytes == 0:
            return 100.0
        return (self.transferred_bytes / self.total_bytes) * 100


def calculate_file_checksum(filepath: str) -> str:
    """
    Calculate SHA-256 checksum of a file.
    
    Args:
        filepath: Path to the file
        
    Returns:
        Hex-encoded SHA-256 hash
    """
    sha256 = hashlib.sha256()
    with open(filepath, 'rb') as f:
        for chunk in iter(lambda: f.read(CHUNK_SIZE), b''):
            sha256.update(chunk)
    return sha256.hexdigest()


class SecureFileTransfer:
    """
    Base class for secure file transfer operations.
    
    Provides common functionality for both sender and receiver.
    """
    
    def __init__(self, connection: SecureTCPConnection):
        """
        Initialize file transfer.
        
        Args:
            connection: Established TCP connection
        """
        self._connection = connection
        self._key_exchange = SecureKeyExchange()
        self._aes_key: Optional[bytes] = None
        self._progress_callback: Optional[Callable[[TransferProgress], None]] = None
        
    def set_progress_callback(self, callback: Callable[[TransferProgress], None]):
        """Set callback for progress updates."""
        self._progress_callback = callback
        
    def _report_progress(self, total: int, transferred: int):
        """Report transfer progress."""
        if self._progress_callback:
            self._progress_callback(TransferProgress(total, transferred))
            
    def _send_typed_message(self, msg_type: bytes, data: bytes) -> bool:
        """
        Send a typed message.
        
        Format: [TYPE (3 bytes)][DATA (variable)]
        """
        message = msg_type + data
        return self._connection.send_message(message)
        
    def _receive_typed_message(self) -> Optional[Tuple[bytes, bytes]]:
        """
        Receive a typed message.
        
        Returns:
            Tuple of (message_type, data) or None on error
        """
        message = self._connection.receive_message()
        if not message or len(message) < 3:
            return None
        return message[:3], message[3:]
        
    def perform_key_exchange(self, is_initiator: bool) -> bool:
        """
        Perform ECDH key exchange.
        
        Args:
            is_initiator: True if this side initiates (sender)
            
        Returns:
            True if key exchange successful
        """
        try:
            self._key_exchange.initialize()
            my_public_key = self._key_exchange.get_public_key_bytes()
            
            if is_initiator:
                # Send our public key first
                logger.info("Sending public key...")
                self._send_typed_message(MSG_TYPE_KEY_EXCHANGE, my_public_key)
                
                # Receive peer's public key
                logger.info("Waiting for peer's public key...")
                msg = self._receive_typed_message()
                if not msg or msg[0] != MSG_TYPE_KEY_EXCHANGE:
                    logger.error("Failed to receive peer's public key")
                    return False
                peer_public_key = msg[1]
            else:
                # Receive peer's public key first
                logger.info("Waiting for peer's public key...")
                msg = self._receive_typed_message()
                if not msg or msg[0] != MSG_TYPE_KEY_EXCHANGE:
                    logger.error("Failed to receive peer's public key")
                    return False
                peer_public_key = msg[1]
                
                # Send our public key
                logger.info("Sending public key...")
                self._send_typed_message(MSG_TYPE_KEY_EXCHANGE, my_public_key)
                
            # Derive shared AES key
            self._key_exchange.set_peer_public_key(peer_public_key)
            self._aes_key = self._key_exchange.get_aes_key()
            
            logger.info("Key exchange complete - AES-256 key derived")
            return True
            
        except Exception as e:
            logger.error(f"Key exchange failed: {e}")
            return False
            
    def cleanup(self):
        """Clean up sensitive data."""
        self._key_exchange.clear()
        if self._aes_key:
            self._aes_key = b'\x00' * len(self._aes_key)
            self._aes_key = None


class FileSender(SecureFileTransfer):
    """
    Secure file sender.
    
    Usage:
        sender = FileSender(tcp_client)
        if sender.perform_key_exchange(is_initiator=True):
            sender.send_file("/path/to/file.pdf")
        sender.cleanup()
    """
    
    def send_file(self, filepath: str) -> bool:
        """
        Send a file securely.
        
        Args:
            filepath: Path to the file to send
            
        Returns:
            True if transfer successful
        """
        if not self._aes_key:
            logger.error("Key exchange not complete")
            return False
            
        # Validate file exists
        if not os.path.exists(filepath):
            logger.error(f"File not found: {filepath}")
            return False
            
        file_path = Path(filepath)
        file_size = file_path.stat().st_size
        
        if file_size > MAX_FILE_SIZE:
            logger.error(f"File too large: {file_size} bytes (max: {MAX_FILE_SIZE})")
            return False
            
        try:
            # Calculate checksum
            logger.info("Calculating file checksum...")
            checksum = calculate_file_checksum(filepath)
            
            # Prepare metadata
            mime_type, _ = mimetypes.guess_type(filepath)
            metadata = FileMetadata(
                filename=file_path.name,
                filesize=file_size,
                checksum=checksum,
                mime_type=mime_type or 'application/octet-stream'
            )
            
            # Send metadata
            logger.info(f"Sending file: {metadata.filename} ({file_size} bytes)")
            if not self._send_typed_message(MSG_TYPE_FILE_METADATA, metadata.to_json()):
                logger.error("Failed to send metadata")
                return False
                
            # Read and encrypt file
            logger.info("Reading and encrypting file...")
            with open(filepath, 'rb') as f:
                plaintext = f.read()
                
            encrypted = encrypt_data(plaintext, self._aes_key)
            
            # Clear plaintext from memory
            del plaintext
            
            # Send encrypted data
            # Format: [IV][TAG][CIPHERTEXT_LENGTH][CIPHERTEXT]
            encrypted_payload = (
                encrypted.iv +
                encrypted.tag +
                struct.pack('>I', len(encrypted.ciphertext)) +
                encrypted.ciphertext
            )
            
            logger.info(f"Sending encrypted data ({len(encrypted_payload)} bytes)...")
            
            if not self._send_typed_message(MSG_TYPE_FILE_DATA, encrypted_payload):
                logger.error("Failed to send file data")
                return False
                
            self._report_progress(file_size, file_size)
            
            # Wait for completion acknowledgment
            msg = self._receive_typed_message()
            if msg and msg[0] == MSG_TYPE_TRANSFER_COMPLETE:
                logger.info("Transfer complete - acknowledged by receiver")
                return True
            elif msg and msg[0] == MSG_TYPE_ERROR:
                error_msg = msg[1].decode('utf-8', errors='ignore')
                logger.error(f"Receiver reported error: {error_msg}")
                return False
            else:
                logger.warning("No acknowledgment received")
                return True  # Transfer might still have succeeded
                
        except Exception as e:
            logger.error(f"Send error: {e}")
            self._send_typed_message(MSG_TYPE_ERROR, str(e).encode('utf-8'))
            return False


class FileReceiver(SecureFileTransfer):
    """
    Secure file receiver.
    
    Usage:
        receiver = FileReceiver(tcp_server)
        if receiver.perform_key_exchange(is_initiator=False):
            filepath = receiver.receive_file("/save/directory")
        receiver.cleanup()
    """
    
    def receive_file(self, save_directory: str) -> Optional[str]:
        """
        Receive a file securely.
        
        Args:
            save_directory: Directory to save the received file
            
        Returns:
            Path to saved file or None on error
        """
        if not self._aes_key:
            logger.error("Key exchange not complete")
            return None
            
        # Ensure save directory exists
        os.makedirs(save_directory, exist_ok=True)
        
        try:
            # Receive metadata
            logger.info("Waiting for file metadata...")
            msg = self._receive_typed_message()
            
            if not msg or msg[0] != MSG_TYPE_FILE_METADATA:
                logger.error("Failed to receive metadata")
                self._send_typed_message(MSG_TYPE_ERROR, b"Expected metadata")
                return None
                
            metadata = FileMetadata.from_json(msg[1])
            logger.info(f"Receiving: {metadata.filename} ({metadata.filesize} bytes)")
            
            # Receive encrypted data
            logger.info("Waiting for encrypted file data...")
            msg = self._receive_typed_message()
            
            if not msg or msg[0] != MSG_TYPE_FILE_DATA:
                logger.error("Failed to receive file data")
                self._send_typed_message(MSG_TYPE_ERROR, b"Expected file data")
                return None
                
            encrypted_payload = msg[1]
            
            # Parse encrypted payload
            if len(encrypted_payload) < IV_SIZE + TAG_SIZE + 4:
                logger.error("Encrypted payload too short")
                self._send_typed_message(MSG_TYPE_ERROR, b"Invalid payload")
                return None
                
            iv = encrypted_payload[:IV_SIZE]
            tag = encrypted_payload[IV_SIZE:IV_SIZE + TAG_SIZE]
            ciphertext_length = struct.unpack('>I', encrypted_payload[IV_SIZE + TAG_SIZE:IV_SIZE + TAG_SIZE + 4])[0]
            ciphertext = encrypted_payload[IV_SIZE + TAG_SIZE + 4:]
            
            if len(ciphertext) != ciphertext_length:
                logger.error(f"Ciphertext length mismatch: expected {ciphertext_length}, got {len(ciphertext)}")
                self._send_typed_message(MSG_TYPE_ERROR, b"Length mismatch")
                return None
                
            encrypted = EncryptedData(iv=iv, tag=tag, ciphertext=ciphertext)
            
            # Decrypt
            logger.info("Decrypting file...")
            try:
                plaintext = decrypt_data(encrypted, self._aes_key)
            except ValueError as e:
                logger.error(f"Decryption failed: {e}")
                self._send_typed_message(MSG_TYPE_ERROR, b"Decryption failed")
                return None
                
            # Verify checksum
            logger.info("Verifying checksum...")
            received_checksum = hashlib.sha256(plaintext).hexdigest()
            
            if received_checksum != metadata.checksum:
                logger.error("Checksum mismatch - file corrupted!")
                self._send_typed_message(MSG_TYPE_ERROR, b"Checksum mismatch")
                return None
                
            # Save file
            save_path = os.path.join(save_directory, metadata.filename)
            
            # Handle filename collision
            base, ext = os.path.splitext(save_path)
            counter = 1
            while os.path.exists(save_path):
                save_path = f"{base}_{counter}{ext}"
                counter += 1
                
            logger.info(f"Saving to: {save_path}")
            with open(save_path, 'wb') as f:
                f.write(plaintext)
                
            # Clear plaintext from memory
            del plaintext
            
            self._report_progress(metadata.filesize, metadata.filesize)
            
            # Send acknowledgment
            self._send_typed_message(MSG_TYPE_TRANSFER_COMPLETE, b"OK")
            
            logger.info("Transfer complete!")
            return save_path
            
        except Exception as e:
            logger.error(f"Receive error: {e}")
            self._send_typed_message(MSG_TYPE_ERROR, str(e).encode('utf-8'))
            return None


# =============================================================================
# High-Level Transfer Functions
# =============================================================================

def send_file_to_receiver(
    host: str,
    port: int,
    filepath: str,
    progress_callback: Optional[Callable[[TransferProgress], None]] = None
) -> bool:
    """
    High-level function to send a file to a receiver.
    
    Args:
        host: Receiver's IP address
        port: Receiver's TCP port
        filepath: Path to file to send
        progress_callback: Optional progress callback
        
    Returns:
        True if transfer successful
    """
    client = TCPClient()
    
    try:
        # Connect
        if not client.connect(host, port):
            return False
            
        # Create sender and transfer
        sender = FileSender(client)
        if progress_callback:
            sender.set_progress_callback(progress_callback)
            
        # Key exchange and send
        if sender.perform_key_exchange(is_initiator=True):
            result = sender.send_file(filepath)
            sender.cleanup()
            return result
        return False
        
    finally:
        client.close()


def receive_file_from_sender(
    port: int,
    save_directory: str,
    progress_callback: Optional[Callable[[TransferProgress], None]] = None,
    timeout: float = 60
) -> Optional[str]:
    """
    High-level function to receive a file from a sender.
    
    Args:
        port: TCP port to listen on
        save_directory: Directory to save received files
        progress_callback: Optional progress callback
        timeout: Timeout for accepting connection
        
    Returns:
        Path to saved file or None
    """
    server = TCPServer(port=port, timeout=timeout)
    
    try:
        # Start server
        if not server.start():
            return None
            
        # Wait for connection
        if not server.accept_connection():
            return None
            
        # Create receiver and transfer
        receiver = FileReceiver(server)
        if progress_callback:
            receiver.set_progress_callback(progress_callback)
            
        # Key exchange and receive
        if receiver.perform_key_exchange(is_initiator=False):
            result = receiver.receive_file(save_directory)
            receiver.cleanup()
            return result
        return None
        
    finally:
        server.close()


# =============================================================================
# Test / Demo
# =============================================================================

if __name__ == "__main__":
    import sys
    import time
    import threading
    
    print("=" * 60)
    print("Secure File Transfer Test")
    print("=" * 60)
    
    # Create test file
    test_dir = "test_transfer"
    os.makedirs(test_dir, exist_ok=True)
    
    test_file = os.path.join(test_dir, "test_file.txt")
    test_content = b"This is a secret test file for secure P2P transfer!\n" * 100
    
    with open(test_file, 'wb') as f:
        f.write(test_content)
    
    print(f"\nCreated test file: {test_file}")
    print(f"Size: {len(test_content)} bytes")
    
    # Progress callback
    def on_progress(progress: TransferProgress):
        print(f"Progress: {progress.percentage:.1f}%")
    
    # Results storage
    results = {'sender': False, 'receiver': None}
    
    # Receiver thread
    def receiver_thread():
        print("\n[RECEIVER] Starting...")
        results['receiver'] = receive_file_from_sender(
            port=5000,
            save_directory=os.path.join(test_dir, "received"),
            progress_callback=on_progress
        )
    
    # Sender thread
    def sender_thread():
        print("\n[SENDER] Starting...")
        time.sleep(1)  # Let receiver start first
        results['sender'] = send_file_to_receiver(
            host="127.0.0.1",
            port=5000,
            filepath=test_file,
            progress_callback=on_progress
        )
    
    # Run test
    recv_t = threading.Thread(target=receiver_thread)
    send_t = threading.Thread(target=sender_thread)
    
    recv_t.start()
    send_t.start()
    
    recv_t.join()
    send_t.join()
    
    # Verify results
    print("\n" + "=" * 60)
    print("Results:")
    print(f"  Sender success: {results['sender']}")
    print(f"  Received file: {results['receiver']}")
    
    if results['receiver']:
        with open(results['receiver'], 'rb') as f:
            received_content = f.read()
        
        if received_content == test_content:
            print("  ✓ Content verified - transfer successful!")
        else:
            print("  ✗ Content mismatch!")
    
    # Cleanup
    import shutil
    shutil.rmtree(test_dir, ignore_errors=True)
    print("\nTest cleanup complete")
