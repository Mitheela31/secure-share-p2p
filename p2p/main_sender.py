#!/usr/bin/env python
"""
Secure P2P File Sender Module.

This module contains the sender-side logic for secure peer-to-peer file transfer.

Features:
=========
1. UDP Discovery - Automatically discovers receivers on the LAN
2. TCP Connection - Establishes secure connection with handshake
3. ECDH Key Exchange - Derives shared secret without exposing private keys
4. AES-256-GCM Encryption - Encrypts files before transmission
5. Integrity Verification - Ensures files aren't tampered during transfer

Usage:
======
    from main_sender import run_sender
    run_sender()

Architecture:
============
    main.py (entry point)
        │
        └── main_sender.py
            │
            ├── discovery.py (UDP listener for receiver broadcasts)
            │
            ├── connection.py (TCP client for secure connection)
            │
            ├── crypto_utils.py (ECDH + HKDF + AES-GCM)
            │
            └── file_transfer.py (Encrypted file transmission)
"""

import os
import sys
import time
import logging
import threading
from typing import Optional, List, Tuple

# Import our modules
from discovery import UDPListener, DISCOVERY_PORT
from connection import TCPClient
from file_transfer import FileSender, TransferProgress
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
APP_NAME = "Secure P2P File Sender"
VERSION = "1.0.0"


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


class SenderApplication:
    """
    Main sender application class.
    
    Provides an interactive console interface for:
    - Discovering receivers on the LAN
    - Selecting a receiver
    - Choosing and sending files securely
    """
    
    def __init__(self):
        """Initialize the sender application."""
        self._listener: Optional[UDPListener] = None
        self._discovered_devices: List[Tuple[str, int]] = []
        self._running = False
        
    def _on_device_discovered(self, ip: str, port: int):
        """Callback when a new receiver is discovered."""
        device = (ip, port)
        if device not in self._discovered_devices:
            self._discovered_devices.append(device)
            print(f"\n  [+] New receiver discovered: {ip}:{port}")
            
    def start_discovery(self):
        """Start the UDP discovery listener."""
        print("  Starting device discovery...")
        print(f"  Listening for receivers on UDP port {DISCOVERY_PORT}")
        print()
        
        self._discovered_devices = []
        self._listener = UDPListener(
            on_device_discovered=self._on_device_discovered,
            stale_timeout=15
        )
        self._listener.start()
        
    def stop_discovery(self):
        """Stop the UDP discovery listener."""
        if self._listener:
            self._listener.stop()
            self._listener = None
            
    def get_discovered_devices(self) -> List[Tuple[str, int]]:
        """Get list of currently discovered devices."""
        if self._listener:
            return self._listener.get_device_list()
        return []
        
    def display_devices(self) -> List[Tuple[str, int]]:
        """Display discovered devices and return the list."""
        devices = self.get_discovered_devices()
        
        if not devices:
            print("  No receivers discovered yet...")
            print("  Make sure the receiver application is running on the same LAN.")
            return []
            
        print("  Available Receivers:")
        print("  " + "-" * 40)
        for i, (ip, port) in enumerate(devices, 1):
            print(f"    {i}. {ip}:{port}")
        print("  " + "-" * 40)
        
        return devices
        
    def select_receiver(self) -> Optional[Tuple[str, int]]:
        """Let user select a receiver from discovered devices."""
        devices = self.display_devices()
        
        if not devices:
            return None
            
        while True:
            try:
                choice = input("\n  Enter receiver number (or 'r' to refresh, 'q' to quit): ").strip()
                
                if choice.lower() == 'q':
                    return None
                if choice.lower() == 'r':
                    devices = self.display_devices()
                    continue
                    
                index = int(choice) - 1
                if 0 <= index < len(devices):
                    return devices[index]
                else:
                    print("  Invalid selection. Try again.")
            except ValueError:
                print("  Invalid input. Enter a number.")
                
    def select_file(self) -> Optional[str]:
        """Let user select a file to send."""
        while True:
            filepath = input("\n  Enter file path to send (or 'q' to quit): ").strip()
            
            if filepath.lower() == 'q':
                return None
                
            # Remove quotes if present
            filepath = filepath.strip('"').strip("'")
            
            if os.path.isfile(filepath):
                return filepath
            else:
                print(f"  File not found: {filepath}")
                print("  Please enter a valid file path.")
                
    def send_file(self, host: str, port: int, filepath: str) -> bool:
        """
        Send a file to the specified receiver.
        
        Args:
            host: Receiver's IP address
            port: Receiver's TCP port
            filepath: Path to the file to send
            
        Returns:
            True if transfer successful
        """
        filename = os.path.basename(filepath)
        filesize = os.path.getsize(filepath)
        
        print(f"\n  File: {filename}")
        print(f"  Size: {filesize:,} bytes")
        print(f"  Receiver: {host}:{port}")
        print()
        
        # Create TCP client
        client = TCPClient()
        
        try:
            # Connect to receiver
            print("  [1/4] Connecting to receiver...")
            if not client.connect(host, port):
                print("  ✗ Connection failed!")
                return False
            print("  ✓ Connected!")
            
            # Create file sender
            sender = FileSender(client)
            sender.set_progress_callback(print_progress_bar)
            
            # Perform key exchange
            print("  [2/4] Performing ECDH key exchange...")
            if not sender.perform_key_exchange(is_initiator=True):
                print("  ✗ Key exchange failed!")
                return False
            print("  ✓ AES-256 session key derived!")
            
            # Encrypt and send file
            print("  [3/4] Encrypting and sending file...")
            if not sender.send_file(filepath):
                print("  ✗ File transfer failed!")
                return False
            print("  ✓ File sent successfully!")
            
            # Cleanup
            print("  [4/4] Cleaning up...")
            sender.cleanup()
            print("  ✓ Secure cleanup complete!")
            
            return True
            
        except Exception as e:
            logger.error(f"Error during transfer: {e}")
            print(f"\n  ✗ Error: {e}")
            return False
            
        finally:
            client.close()
            
    def run(self):
        """Run the interactive sender application."""
        self._running = True
        
        try:
            clear_screen()
            print_header()
            
            print("  Press Ctrl+C at any time to exit.\n")
            
            # Start discovery
            self.start_discovery()
            
            print("  Searching for receivers on LAN...")
            print("  (Receivers broadcast every 3 seconds)\n")
            
            # Wait a bit for initial discovery
            time.sleep(4)
            
            while self._running:
                # Select receiver
                print("\n" + "=" * 60)
                print("  STEP 1: Select Receiver")
                print("=" * 60)
                
                receiver = self.select_receiver()
                if not receiver:
                    continue
                    
                host, port = receiver
                print(f"\n  Selected: {host}:{port}")
                
                # Select file
                print("\n" + "=" * 60)
                print("  STEP 2: Select File")
                print("=" * 60)
                
                filepath = self.select_file()
                if not filepath:
                    continue
                    
                # Confirm
                print("\n" + "=" * 60)
                print("  STEP 3: Confirm Transfer")
                print("=" * 60)
                
                print(f"\n  File: {os.path.basename(filepath)}")
                print(f"  Size: {os.path.getsize(filepath):,} bytes")
                print(f"  To: {host}:{port}")
                
                confirm = input("\n  Send this file? (y/n): ").strip().lower()
                if confirm != 'y':
                    print("  Transfer cancelled.")
                    continue
                    
                # Send file
                print("\n" + "=" * 60)
                print("  STEP 4: Secure Transfer")
                print("=" * 60)
                print()
                
                success = self.send_file(host, port, filepath)
                
                print("\n" + "=" * 60)
                if success:
                    print("  ✓ FILE TRANSFERRED SUCCESSFULLY!")
                else:
                    print("  ✗ FILE TRANSFER FAILED!")
                print("=" * 60)
                
                # Ask if user wants to send another file
                another = input("\n  Send another file? (y/n): ").strip().lower()
                if another != 'y':
                    break
                    
        except KeyboardInterrupt:
            print("\n\n  Shutting down...")
            
        finally:
            self.stop_discovery()
            print("\n  Goodbye!\n")


# =============================================================================
# Public Entry Point
# =============================================================================

def run_sender():
    """
    Run the sender application.
    
    This is the main entry point for sender mode.
    Called from main.py when user selects 'Start as Sender'.
    """
    app = SenderApplication()
    app.run()
