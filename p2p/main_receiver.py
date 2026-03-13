#!/usr/bin/env python
"""
Secure P2P File Receiver Module.

This module contains the receiver-side logic for secure peer-to-peer file transfer.

Features:
=========
1. UDP Broadcast - Advertises presence to senders on the LAN
2. TCP Server - Listens for incoming connections with handshake
3. ECDH Key Exchange - Derives shared secret without exposing private keys
4. AES-256-GCM Decryption - Decrypts received files securely
5. Integrity Verification - Verifies files weren't tampered during transfer

Usage:
======
    from main_receiver import run_receiver
    run_receiver()

Architecture:
============
    main.py (entry point)
        │
        └── main_receiver.py
            │
            ├── discovery.py (UDP broadcaster to announce presence)
            │
            ├── connection.py (TCP server for secure connection)
            │
            ├── crypto_utils.py (ECDH + HKDF + AES-GCM)
            │
            └── file_transfer.py (Encrypted file reception)
"""

import os
import sys
import time
import logging
import threading
from typing import Optional
from pathlib import Path

# Import our modules
from discovery import UDPBroadcaster, DISCOVERY_PORT
from connection import TCPServer, DEFAULT_TCP_PORT
from file_transfer import FileReceiver, TransferProgress
from crypto_utils import AES_KEY_SIZE

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Application constants
APP_NAME = "Secure P2P File Receiver"
VERSION = "1.0.0"
DEFAULT_SAVE_DIR = "received_files"


def clear_screen():
    """Clear the console screen."""
    os.system('cls' if os.name == 'nt' else 'clear')


def print_header():
    """Print application header."""
    print("=" * 60)
    print(f"  {APP_NAME} v{VERSION}")
    print("=" * 60)
    print()


def print_progress_bar(progress: TransferProgress):
    """Print a progress bar for file transfer."""
    width = 40
    filled = int(width * progress.transferred_bytes / max(progress.total_bytes, 1))
    bar = "█" * filled + "░" * (width - filled)
    percentage = progress.percentage
    
    sys.stdout.write(f"\r  Progress: [{bar}] {percentage:.1f}%")
    sys.stdout.flush()
    
    if progress.transferred_bytes >= progress.total_bytes:
        print()  # New line when complete


def get_local_ip():
    """Get the local IP address."""
    import socket
    try:
        # Connect to external address to determine local IP
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


class ReceiverApplication:
    """
    Main receiver application class.
    
    Provides an interactive console interface for:
    - Broadcasting presence on the LAN
    - Accepting incoming connections
    - Receiving files securely
    """
    
    def __init__(self, tcp_port: int = DEFAULT_TCP_PORT, save_directory: str = DEFAULT_SAVE_DIR):
        """
        Initialize the receiver application.
        
        Args:
            tcp_port: TCP port for file transfers
            save_directory: Directory to save received files
        """
        self._tcp_port = tcp_port
        self._save_directory = save_directory
        self._broadcaster: Optional[UDPBroadcaster] = None
        self._running = False
        
    def start_broadcasting(self):
        """Start the UDP discovery broadcaster."""
        local_ip = get_local_ip()
        
        print(f"  Local IP: {local_ip}")
        print(f"  TCP Port: {self._tcp_port}")
        print(f"  UDP Discovery Port: {DISCOVERY_PORT}")
        print()
        print("  Starting device broadcast...")
        print(f"  Broadcasting: SECURE_SHARE:{self._tcp_port}")
        print()
        
        self._broadcaster = UDPBroadcaster(
            tcp_port=self._tcp_port,
            broadcast_interval=3
        )
        self._broadcaster.start()
        
    def stop_broadcasting(self):
        """Stop the UDP discovery broadcaster."""
        if self._broadcaster:
            self._broadcaster.stop()
            self._broadcaster = None
            
    def wait_for_connection(self, timeout: float = 60) -> Optional[TCPServer]:
        """
        Wait for an incoming connection.
        
        Args:
            timeout: Timeout in seconds
            
        Returns:
            TCPServer with connected client, or None on timeout
        """
        server = TCPServer(port=self._tcp_port, timeout=timeout)
        
        if not server.start():
            print("  ✗ Failed to start TCP server!")
            return None
            
        print(f"  Waiting for sender to connect (timeout: {timeout}s)...")
        print("  (Send a file from the sender application)\n")
        
        if server.accept_connection():
            client_addr = server.client_address
            print(f"\n  ✓ Sender connected from: {client_addr[0]}:{client_addr[1]}")
            return server
        else:
            server.close()
            return None
            
    def receive_file(self, server: TCPServer) -> Optional[str]:
        """
        Receive a file from the connected sender.
        
        Args:
            server: TCP server with connected client
            
        Returns:
            Path to saved file or None on error
        """
        # Ensure save directory exists
        os.makedirs(self._save_directory, exist_ok=True)
        
        # Create file receiver
        receiver = FileReceiver(server)
        receiver.set_progress_callback(print_progress_bar)
        
        try:
            # Perform key exchange
            print("\n  [1/3] Performing ECDH key exchange...")
            if not receiver.perform_key_exchange(is_initiator=False):
                print("  ✗ Key exchange failed!")
                return None
            print("  ✓ AES-256 session key derived!")
            
            # Receive and decrypt file
            print("  [2/3] Receiving and decrypting file...")
            filepath = receiver.receive_file(self._save_directory)
            
            if not filepath:
                print("  ✗ File reception failed!")
                return None
            print(f"  ✓ File received: {os.path.basename(filepath)}")
            
            # Cleanup
            print("  [3/3] Cleaning up...")
            receiver.cleanup()
            print("  ✓ Secure cleanup complete!")
            
            return filepath
            
        except Exception as e:
            logger.error(f"Error during reception: {e}")
            print(f"\n  ✗ Error: {e}")
            return None
            
    def run_single_transfer(self) -> bool:
        """
        Run a single file transfer cycle.
        
        Returns:
            True if a file was successfully received
        """
        # Wait for connection
        print("\n" + "=" * 60)
        print("  WAITING FOR SENDER")
        print("=" * 60)
        print()
        
        server = self.wait_for_connection(timeout=300)  # 5 minute timeout
        
        if not server:
            print("\n  No sender connected within timeout.")
            return False
            
        try:
            # Receive file
            print("\n" + "=" * 60)
            print("  RECEIVING FILE")
            print("=" * 60)
            
            filepath = self.receive_file(server)
            
            print("\n" + "=" * 60)
            if filepath:
                print("  ✓ FILE RECEIVED SUCCESSFULLY!")
                print(f"  Saved to: {filepath}")
                print(f"  Size: {os.path.getsize(filepath):,} bytes")
            else:
                print("  ✗ FILE RECEPTION FAILED!")
            print("=" * 60)
            
            return filepath is not None
            
        finally:
            server.close()
            
    def run(self):
        """Run the interactive receiver application."""
        self._running = True
        
        try:
            clear_screen()
            print_header()
            
            print("  Press Ctrl+C at any time to exit.\n")
            
            # Get settings
            print("=" * 60)
            print("  CONFIGURATION")
            print("=" * 60)
            print()
            
            # Get save directory
            save_dir_input = input(f"  Save directory [{self._save_directory}]: ").strip()
            if save_dir_input:
                self._save_directory = save_dir_input
                
            # Get TCP port
            port_input = input(f"  TCP port [{self._tcp_port}]: ").strip()
            if port_input:
                try:
                    self._tcp_port = int(port_input)
                except ValueError:
                    print(f"  Invalid port, using default: {self._tcp_port}")
                    
            print()
            
            # Create save directory
            os.makedirs(self._save_directory, exist_ok=True)
            save_path = os.path.abspath(self._save_directory)
            print(f"  Files will be saved to: {save_path}")
            print()
            
            # Start broadcasting
            print("=" * 60)
            print("  STARTING RECEIVER")
            print("=" * 60)
            print()
            
            self.start_broadcasting()
            
            print("  ✓ Receiver is now visible to senders on the LAN")
            print("  ✓ Waiting for incoming file transfers...")
            
            # Main loop
            while self._running:
                success = self.run_single_transfer()
                
                if self._running:
                    # Ask if user wants to receive another file
                    another = input("\n  Wait for another file? (y/n): ").strip().lower()
                    if another != 'y':
                        break
                        
        except KeyboardInterrupt:
            print("\n\n  Shutting down...")
            
        finally:
            self.stop_broadcasting()
            print("\n  Goodbye!\n")


# =============================================================================
# Public Entry Point
# =============================================================================

def run_receiver(tcp_port: int = DEFAULT_TCP_PORT, save_directory: str = DEFAULT_SAVE_DIR):
    """
    Run the receiver application.
    
    This is the main entry point for receiver mode.
    Called from main.py when user selects 'Start as Receiver'.
    
    Args:
        tcp_port: TCP port for file transfers (default: 5000)
        save_directory: Directory to save received files (default: received_files)
    """
    app = ReceiverApplication(
        tcp_port=tcp_port,
        save_directory=save_directory
    )
    app.run()
