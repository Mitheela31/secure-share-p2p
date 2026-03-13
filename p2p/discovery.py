"""
UDP Discovery Module for LAN-based Peer-to-Peer File Sharing.

Architecture:
============
This module implements automatic device discovery within a LAN using UDP broadcast.

RECEIVER broadcasts its presence:
    - Sends "SECURE_SHARE:<tcp_port>" every 3 seconds
    - Uses broadcast address 255.255.255.255 on port 9999
    
SENDER listens for broadcasts:
    - Receives broadcast messages
    - Extracts IP and TCP port of available receivers
    - Maintains list of discovered devices

Threading:
==========
Both broadcaster and listener run in separate threads to avoid blocking the main UI.
Uses daemon threads that automatically terminate when the main program exits.

Security Notes:
===============
- Discovery only reveals IP and port, no sensitive data
- Actual file transfer happens over secure TCP with encryption
"""

import socket
import threading
import time
import logging
from typing import Dict, Callable, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Protocol constants
DISCOVERY_PORT = 9999
BROADCAST_ADDRESS = '255.255.255.255'
BROADCAST_INTERVAL = 3  # seconds
PROTOCOL_PREFIX = 'SECURE_SHARE:'
SOCKET_TIMEOUT = 5  # seconds


@dataclass
class DiscoveredDevice:
    """Represents a discovered peer device on the LAN."""
    ip: str
    tcp_port: int
    last_seen: datetime
    
    def is_stale(self, timeout_seconds: int = 10) -> bool:
        """Check if the device hasn't been seen recently."""
        elapsed = (datetime.now() - self.last_seen).total_seconds()
        return elapsed > timeout_seconds


class UDPBroadcaster:
    """
    UDP Broadcaster for receiver to advertise its presence.
    
    Usage:
        broadcaster = UDPBroadcaster(tcp_port=5000)
        broadcaster.start()
        # ... application runs ...
        broadcaster.stop()
    """
    
    def __init__(self, tcp_port: int, broadcast_interval: float = BROADCAST_INTERVAL):
        """
        Initialize the UDP broadcaster.
        
        Args:
            tcp_port: The TCP port where the receiver will accept connections
            broadcast_interval: Time between broadcasts in seconds
        """
        self.tcp_port = tcp_port
        self.broadcast_interval = broadcast_interval
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._socket: Optional[socket.socket] = None
        
    def _create_broadcast_socket(self) -> socket.socket:
        """Create and configure UDP socket for broadcasting."""
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        # Enable broadcast mode
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        # Allow address reuse
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        return sock
    
    def _broadcast_loop(self):
        """Main broadcast loop - runs in separate thread."""
        logger.info(f"Starting UDP broadcast on port {DISCOVERY_PORT}")
        
        try:
            self._socket = self._create_broadcast_socket()
            message = f"{PROTOCOL_PREFIX}{self.tcp_port}".encode('utf-8')
            
            while not self._stop_event.is_set():
                try:
                    # Broadcast to all devices on the LAN
                    self._socket.sendto(message, (BROADCAST_ADDRESS, DISCOVERY_PORT))
                    logger.debug(f"Broadcast sent: {message.decode()}")
                except OSError as e:
                    logger.warning(f"Broadcast failed: {e}")
                
                # Wait for interval or stop signal
                self._stop_event.wait(self.broadcast_interval)
                
        except Exception as e:
            logger.error(f"Broadcaster error: {e}")
        finally:
            self._cleanup()
            
    def _cleanup(self):
        """Clean up socket resources."""
        if self._socket:
            try:
                self._socket.close()
                logger.debug("Broadcast socket closed")
            except Exception as e:
                logger.warning(f"Error closing socket: {e}")
            self._socket = None
            
    def start(self):
        """Start the broadcaster in a background thread."""
        if self._thread and self._thread.is_alive():
            logger.warning("Broadcaster already running")
            return
            
        self._stop_event.clear()
        self._thread = threading.Thread(
            target=self._broadcast_loop,
            name="UDPBroadcaster",
            daemon=True
        )
        self._thread.start()
        logger.info("Broadcaster started")
        
    def stop(self):
        """Stop the broadcaster gracefully."""
        logger.info("Stopping broadcaster...")
        self._stop_event.set()
        
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=self.broadcast_interval + 1)
            
        self._cleanup()
        logger.info("Broadcaster stopped")
        
    def is_running(self) -> bool:
        """Check if broadcaster is currently running."""
        return self._thread is not None and self._thread.is_alive()


class UDPListener:
    """
    UDP Listener for sender to discover available receivers.
    
    Usage:
        def on_device_found(ip, port):
            print(f"Found device: {ip}:{port}")
            
        listener = UDPListener(on_device_discovered=on_device_found)
        listener.start()
        
        # Get all discovered devices
        devices = listener.get_discovered_devices()
    """
    
    def __init__(
        self,
        on_device_discovered: Optional[Callable[[str, int], None]] = None,
        stale_timeout: int = 10
    ):
        """
        Initialize the UDP listener.
        
        Args:
            on_device_discovered: Callback when new device is found (ip, port)
            stale_timeout: Seconds before a device is considered stale
        """
        self._on_device_discovered = on_device_discovered
        self._stale_timeout = stale_timeout
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._socket: Optional[socket.socket] = None
        self._discovered_devices: Dict[str, DiscoveredDevice] = {}
        self._devices_lock = threading.Lock()
        
    def _create_listener_socket(self) -> socket.socket:
        """Create and configure UDP socket for listening."""
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        # Bind to all interfaces on discovery port
        sock.bind(('', DISCOVERY_PORT))
        sock.settimeout(SOCKET_TIMEOUT)
        return sock
    
    def _parse_broadcast_message(self, data: bytes) -> Optional[int]:
        """
        Parse a broadcast message and extract TCP port.
        
        Args:
            data: Raw bytes received
            
        Returns:
            TCP port if valid message, None otherwise
        """
        try:
            message = data.decode('utf-8')
            if message.startswith(PROTOCOL_PREFIX):
                port_str = message[len(PROTOCOL_PREFIX):]
                port = int(port_str)
                if 1 <= port <= 65535:
                    return port
        except (UnicodeDecodeError, ValueError) as e:
            logger.debug(f"Invalid broadcast message: {e}")
        return None
    
    def _listen_loop(self):
        """Main listen loop - runs in separate thread."""
        logger.info(f"Starting UDP listener on port {DISCOVERY_PORT}")
        
        try:
            self._socket = self._create_listener_socket()
            
            while not self._stop_event.is_set():
                try:
                    data, addr = self._socket.recvfrom(1024)
                    sender_ip = addr[0]
                    
                    tcp_port = self._parse_broadcast_message(data)
                    if tcp_port:
                        self._handle_discovered_device(sender_ip, tcp_port)
                        
                except socket.timeout:
                    # Normal timeout, check for stop signal
                    self._remove_stale_devices()
                    continue
                except OSError as e:
                    if not self._stop_event.is_set():
                        logger.warning(f"Receive error: {e}")
                        
        except Exception as e:
            logger.error(f"Listener error: {e}")
        finally:
            self._cleanup()
            
    def _handle_discovered_device(self, ip: str, tcp_port: int):
        """Handle a discovered device."""
        device_key = f"{ip}:{tcp_port}"
        is_new = False
        
        with self._devices_lock:
            if device_key not in self._discovered_devices:
                is_new = True
                logger.info(f"New device discovered: {ip}:{tcp_port}")
                
            self._discovered_devices[device_key] = DiscoveredDevice(
                ip=ip,
                tcp_port=tcp_port,
                last_seen=datetime.now()
            )
            
        # Notify callback for new devices
        if is_new and self._on_device_discovered:
            try:
                self._on_device_discovered(ip, tcp_port)
            except Exception as e:
                logger.error(f"Callback error: {e}")
                
    def _remove_stale_devices(self):
        """Remove devices that haven't been seen recently."""
        with self._devices_lock:
            stale_keys = [
                key for key, device in self._discovered_devices.items()
                if device.is_stale(self._stale_timeout)
            ]
            for key in stale_keys:
                logger.debug(f"Removing stale device: {key}")
                del self._discovered_devices[key]
                
    def _cleanup(self):
        """Clean up socket resources."""
        if self._socket:
            try:
                self._socket.close()
                logger.debug("Listener socket closed")
            except Exception as e:
                logger.warning(f"Error closing socket: {e}")
            self._socket = None
            
    def start(self):
        """Start the listener in a background thread."""
        if self._thread and self._thread.is_alive():
            logger.warning("Listener already running")
            return
            
        self._stop_event.clear()
        self._thread = threading.Thread(
            target=self._listen_loop,
            name="UDPListener",
            daemon=True
        )
        self._thread.start()
        logger.info("Listener started")
        
    def stop(self):
        """Stop the listener gracefully."""
        logger.info("Stopping listener...")
        self._stop_event.set()
        
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=SOCKET_TIMEOUT + 1)
            
        self._cleanup()
        logger.info("Listener stopped")
        
    def is_running(self) -> bool:
        """Check if listener is currently running."""
        return self._thread is not None and self._thread.is_alive()
    
    def get_discovered_devices(self) -> Dict[str, DiscoveredDevice]:
        """
        Get all currently discovered devices.
        
        Returns:
            Dictionary of device_key -> DiscoveredDevice
        """
        with self._devices_lock:
            # Return a copy to avoid threading issues
            return dict(self._discovered_devices)
            
    def get_device_list(self) -> list[Tuple[str, int]]:
        """
        Get list of discovered devices as (ip, port) tuples.
        
        Returns:
            List of (ip, port) tuples
        """
        with self._devices_lock:
            return [(d.ip, d.tcp_port) for d in self._discovered_devices.values()]
            
    def clear_devices(self):
        """Clear all discovered devices."""
        with self._devices_lock:
            self._discovered_devices.clear()


# =============================================================================
# Convenience functions for simple usage
# =============================================================================

def start_broadcasting(tcp_port: int) -> UDPBroadcaster:
    """
    Start broadcasting receiver presence.
    
    Args:
        tcp_port: TCP port where receiver will accept connections
        
    Returns:
        Running UDPBroadcaster instance
    """
    broadcaster = UDPBroadcaster(tcp_port)
    broadcaster.start()
    return broadcaster


def start_listening(
    on_discovered: Optional[Callable[[str, int], None]] = None
) -> UDPListener:
    """
    Start listening for receiver broadcasts.
    
    Args:
        on_discovered: Callback function(ip, port) when device found
        
    Returns:
        Running UDPListener instance
    """
    listener = UDPListener(on_device_discovered=on_discovered)
    listener.start()
    return listener


# =============================================================================
# Test / Demo
# =============================================================================

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python discovery.py [broadcast|listen]")
        sys.exit(1)
        
    mode = sys.argv[1].lower()
    
    if mode == "broadcast":
        # Test as receiver (broadcast mode)
        print("Starting broadcaster on TCP port 5000...")
        broadcaster = start_broadcasting(5000)
        
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\nShutting down...")
            broadcaster.stop()
            
    elif mode == "listen":
        # Test as sender (listen mode)
        def on_found(ip, port):
            print(f">>> DISCOVERED: {ip}:{port}")
            
        print("Starting listener for receivers...")
        listener = start_listening(on_discovered=on_found)
        
        try:
            while True:
                time.sleep(5)
                devices = listener.get_device_list()
                print(f"Active devices: {devices}")
        except KeyboardInterrupt:
            print("\nShutting down...")
            listener.stop()
    else:
        print(f"Unknown mode: {mode}")
        sys.exit(1)
