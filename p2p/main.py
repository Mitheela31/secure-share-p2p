#!/usr/bin/env python
"""
Secure P2P File Sharing System - Main Entry Point.

This is the unified entry point for the secure peer-to-peer file sharing application.
It allows users to run either as a Sender or Receiver from a single executable.

Features:
=========
- Single executable for both sender and receiver modes
- Interactive mode selection at startup
- UDP broadcast discovery for LAN device detection
- TCP secure connection with handshake verification
- ECDH key exchange for secure key derivation
- AES-256-GCM encryption for file transfer
- Integrity verification via checksums

Usage:
======
    python main.py

    Then select:
        1. Start as Receiver - Wait for files from senders
        2. Start as Sender   - Send files to discovered receivers

Building Single Executable:
===========================
    pip install pyinstaller
    pyinstaller --onefile --name SecureShare main.py

Architecture:
============
    main.py (this file - entry point)
        │
        ├── main_receiver.py (receiver mode logic)
        │       │
        │       └── discovery.py, connection.py, crypto_utils.py, file_transfer.py
        │
        └── main_sender.py (sender mode logic)
                │
                └── discovery.py, connection.py, crypto_utils.py, file_transfer.py
"""

import os
import sys

# Application metadata
APP_NAME = "Secure P2P File Sharing System"
VERSION = "1.0.0"


def clear_screen():
    """Clear the console screen."""
    os.system('cls' if os.name == 'nt' else 'clear')


def print_banner():
    """Print the application banner."""
    print()
    print("=" * 60)
    print(f"  {APP_NAME}")
    print(f"  Version {VERSION}")
    print("=" * 60)
    print()
    print("  Secure LAN-based peer-to-peer file transfer")
    print("  using AES-256-GCM encryption with ECDH key exchange")
    print()
    print("-" * 60)
    print()


def print_menu():
    """Print the mode selection menu."""
    print("  Select Mode:")
    print()
    print("    1. Start as Receiver")
    print("       - Broadcast presence on LAN")
    print("       - Wait for senders to connect")
    print("       - Receive and decrypt files")
    print()
    print("    2. Start as Sender")
    print("       - Discover receivers on LAN")
    print("       - Connect and send files securely")
    print()
    print("    q. Quit")
    print()
    print("-" * 60)


def main():
    """
    Main entry point for the application.
    
    Displays a menu for the user to select between:
    - Receiver mode: Waits for incoming file transfers
    - Sender mode: Discovers receivers and sends files
    """
    # Import here to avoid issues if modules have initialization code
    from main_receiver import run_receiver
    from main_sender import run_sender
    
    clear_screen()
    print_banner()
    print_menu()
    
    while True:
        choice = input("  Enter your choice (1/2/q): ").strip().lower()
        
        if choice == '1':
            print()
            print("  Starting Receiver Mode...")
            print()
            run_receiver()
            break
            
        elif choice == '2':
            print()
            print("  Starting Sender Mode...")
            print()
            run_sender()
            break
            
        elif choice == 'q':
            print()
            print("  Goodbye!")
            print()
            sys.exit(0)
            
        else:
            print()
            print("  Invalid choice. Please enter 1, 2, or q.")
            print()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n  Interrupted. Goodbye!\n")
        sys.exit(0)
