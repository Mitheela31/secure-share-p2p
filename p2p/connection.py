"""
TCP Connection Module for Secure Peer-to-Peer File Transfer.

Architecture:
============
This module handles TCP connections between sender and receiver after UDP discovery.

RECEIVER (Server):
    - Opens TCP socket on advertised port
    - Listens for incoming connections
    - Validates handshake before accepting
    
SENDER (Client):
    - Connects to discovered receiver
    - Sends handshake for validation
    - Proceeds with secure file transfer

Handshake Protocol:
==================
1. Client connects to server
2. Client sends: "SECURE_SHARE_HANDSHAKE"
3. Server validates and responds: "HANDSHAKE_ACCEPTED"
4. If invalid, server closes connection

Security Notes:
===============
- Handshake prevents accidental connections
- All sensitive data transfer happens after ECDH key exchange
- Sockets are properly closed on error
"""

import socket
import struct
import threading
import logging
from typing import Optional, Callable, Tuple
from enum import Enum, auto
from dataclasses import dataclass

# Configure logging
logger = logging.getLogger(__name__)

# Protocol constants
HANDSHAKE_REQUEST = b"SECURE_SHARE_HANDSHAKE"
HANDSHAKE_RESPONSE = b"HANDSHAKE_ACCEPTED"
HANDSHAKE_REJECTED = b"HANDSHAKE_REJECTED"
DEFAULT_TCP_PORT = 5000
SOCKET_TIMEOUT = 30  # seconds
BACKLOG = 5  # Max pending connections
BUFFER_SIZE = 4096


class ConnectionState(Enum):
    """Connection state machine states."""
    DISCONNECTED = auto()
    CONNECTING = auto()
    HANDSHAKING = auto()
    CONNECTED = auto()
    ERROR = auto()


@dataclass
class ConnectionInfo:
    """Information about an established connection."""
    local_address: Tuple[str, int]
    remote_address: Tuple[str, int]
    state: ConnectionState


class SecureTCPConnection:
    """
    Base class for secure TCP connections.
    
    Provides common functionality for both server and client sides:
    - Socket management
    - Length-prefixed message protocol
    - Handshake validation
    - Graceful shutdown
    """
    
    def __init__(self, timeout: float = SOCKET_TIMEOUT):
        """
        Initialize connection.
        
        Args:
            timeout: Socket timeout in seconds
        """
        self._socket: Optional[socket.socket] = None
        self._timeout = timeout
        self._state = ConnectionState.DISCONNECTED
        self._lock = threading.Lock()
        
    @property
    def state(self) -> ConnectionState:
        """Get current connection state."""
        return self._state
        
    @property
    def is_connected(self) -> bool:
        """Check if connection is established."""
        return self._state == ConnectionState.CONNECTED
        
    def _set_state(self, state: ConnectionState):
        """Thread-safe state update."""
        with self._lock:
            self._state = state
            
    def send_message(self, data: bytes) -> bool:
        """
        Send a length-prefixed message.
        
        Protocol: [4-byte length][payload]
        
        Args:
            data: Bytes to send
            
        Returns:
            True if successful, False otherwise
        """
        if not self._socket:
            logger.error("Cannot send: no socket")
            return False
            
        try:
            # Prefix with 4-byte length (big-endian)
            length = len(data)
            header = struct.pack('>I', length)
            self._socket.sendall(header + data)
            logger.debug(f"Sent {length} bytes")
            return True
        except Exception as e:
            logger.error(f"Send error: {e}")
            self._set_state(ConnectionState.ERROR)
            return False
            
    def receive_message(self) -> Optional[bytes]:
        """
        Receive a length-prefixed message.
        
        Returns:
            Received bytes or None on error
        """
        if not self._socket:
            logger.error("Cannot receive: no socket")
            return None
            
        try:
            # Read 4-byte length header
            header = self._recv_exact(4)
            if not header:
                return None
                
            length = struct.unpack('>I', header)[0]
            
            # Sanity check on length (max 100MB)
            if length > 100 * 1024 * 1024:
                logger.error(f"Message too large: {length} bytes")
                return None
                
            # Read the payload
            data = self._recv_exact(length)
            logger.debug(f"Received {length} bytes")
            return data
            
        except Exception as e:
            logger.error(f"Receive error: {e}")
            self._set_state(ConnectionState.ERROR)
            return None
            
    def _recv_exact(self, num_bytes: int) -> Optional[bytes]:
        """
        Receive exactly num_bytes from socket.
        
        Args:
            num_bytes: Number of bytes to receive
            
        Returns:
            Received bytes or None on error
        """
        data = b''
        while len(data) < num_bytes:
            try:
                chunk = self._socket.recv(num_bytes - len(data))
                if not chunk:
                    logger.warning("Connection closed by peer")
                    return None
                data += chunk
            except socket.timeout:
                logger.warning("Socket timeout")
                return None
            except Exception as e:
                logger.error(f"Recv error: {e}")
                return None
        return data
        
    def send_raw(self, data: bytes) -> bool:
        """
        Send raw bytes without length prefix.
        Used for handshake messages.
        
        Args:
            data: Bytes to send
            
        Returns:
            True if successful
        """
        if not self._socket:
            return False
        try:
            self._socket.sendall(data)
            return True
        except Exception as e:
            logger.error(f"Send raw error: {e}")
            return False
            
    def recv_raw(self, size: int) -> Optional[bytes]:
        """
        Receive raw bytes without length prefix.
        Used for handshake messages.
        
        Args:
            size: Number of bytes to receive
            
        Returns:
            Received bytes or None
        """
        if not self._socket:
            return None
        try:
            return self._socket.recv(size)
        except Exception as e:
            logger.error(f"Recv raw error: {e}")
            return None
            
    def get_connection_info(self) -> Optional[ConnectionInfo]:
        """Get information about current connection."""
        if not self._socket:
            return None
        try:
            return ConnectionInfo(
                local_address=self._socket.getsockname(),
                remote_address=self._socket.getpeername(),
                state=self._state
            )
        except Exception:
            return None
            
    def close(self):
        """Close the connection gracefully."""
        if self._socket:
            try:
                self._socket.shutdown(socket.SHUT_RDWR)
            except Exception:
                pass  # May already be closed
            try:
                self._socket.close()
            except Exception:
                pass
            self._socket = None
        self._set_state(ConnectionState.DISCONNECTED)
        logger.info("Connection closed")


class TCPServer(SecureTCPConnection):
    """
    TCP Server for receiver side.
    
    Usage:
        server = TCPServer(port=5000)
        server.start()
        
        # Wait for connection
        if server.accept_connection():
            # Connection established, proceed with key exchange
            pass
            
        server.close()
    """
    
    def __init__(self, port: int = DEFAULT_TCP_PORT, timeout: float = SOCKET_TIMEOUT):
        """
        Initialize TCP server.
        
        Args:
            port: Port to listen on
            timeout: Socket timeout in seconds
        """
        super().__init__(timeout)
        self._port = port
        self._server_socket: Optional[socket.socket] = None
        self._client_address: Optional[Tuple[str, int]] = None
        
    def start(self) -> bool:
        """
        Start the server and begin listening.
        
        Returns:
            True if server started successfully
        """
        try:
            self._server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self._server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self._server_socket.bind(('', self._port))
            self._server_socket.listen(BACKLOG)
            self._server_socket.settimeout(self._timeout)
            
            logger.info(f"TCP Server listening on port {self._port}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to start server: {e}")
            self._set_state(ConnectionState.ERROR)
            return False
            
    def accept_connection(self) -> bool:
        """
        Wait for and accept a client connection with handshake.
        
        Returns:
            True if valid client connected
        """
        if not self._server_socket:
            logger.error("Server not started")
            return False
            
        self._set_state(ConnectionState.CONNECTING)
        
        try:
            logger.info("Waiting for client connection...")
            client_socket, client_address = self._server_socket.accept()
            self._client_address = client_address
            client_socket.settimeout(self._timeout)
            
            logger.info(f"Connection from {client_address}")
            
            # Validate handshake
            self._socket = client_socket
            self._set_state(ConnectionState.HANDSHAKING)
            
            if self._validate_handshake():
                self._set_state(ConnectionState.CONNECTED)
                logger.info(f"Handshake successful with {client_address}")
                return True
            else:
                logger.warning(f"Handshake failed with {client_address}")
                self._socket.close()
                self._socket = None
                self._set_state(ConnectionState.DISCONNECTED)
                return False
                
        except socket.timeout:
            logger.info("Accept timeout - no client connected")
            return False
        except Exception as e:
            logger.error(f"Accept error: {e}")
            self._set_state(ConnectionState.ERROR)
            return False
            
    def _validate_handshake(self) -> bool:
        """
        Validate client handshake.
        
        Returns:
            True if handshake is valid
        """
        try:
            # Receive handshake request
            data = self.recv_raw(len(HANDSHAKE_REQUEST))
            
            if data == HANDSHAKE_REQUEST:
                # Send acceptance
                self.send_raw(HANDSHAKE_RESPONSE)
                return True
            else:
                # Send rejection
                self.send_raw(HANDSHAKE_REJECTED)
                logger.warning(f"Invalid handshake received: {data}")
                return False
                
        except Exception as e:
            logger.error(f"Handshake error: {e}")
            return False
            
    def close(self):
        """Close server and client sockets."""
        super().close()
        if self._server_socket:
            try:
                self._server_socket.close()
            except Exception:
                pass
            self._server_socket = None
        logger.info("Server stopped")
        
    @property
    def port(self) -> int:
        """Get server port."""
        return self._port
        
    @property
    def client_address(self) -> Optional[Tuple[str, int]]:
        """Get connected client's address."""
        return self._client_address


class TCPClient(SecureTCPConnection):
    """
    TCP Client for sender side.
    
    Usage:
        client = TCPClient()
        if client.connect(receiver_ip, receiver_port):
            # Connection established, proceed with key exchange
            pass
        client.close()
    """
    
    def __init__(self, timeout: float = SOCKET_TIMEOUT):
        """
        Initialize TCP client.
        
        Args:
            timeout: Socket timeout in seconds
        """
        super().__init__(timeout)
        self._server_address: Optional[Tuple[str, int]] = None
        
    def connect(self, host: str, port: int) -> bool:
        """
        Connect to receiver and perform handshake.
        
        Args:
            host: Receiver IP address
            port: Receiver TCP port
            
        Returns:
            True if connected and handshake successful
        """
        self._server_address = (host, port)
        self._set_state(ConnectionState.CONNECTING)
        
        try:
            self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self._socket.settimeout(self._timeout)
            
            logger.info(f"Connecting to {host}:{port}...")
            self._socket.connect((host, port))
            
            logger.info("Connected, performing handshake...")
            self._set_state(ConnectionState.HANDSHAKING)
            
            if self._perform_handshake():
                self._set_state(ConnectionState.CONNECTED)
                logger.info("Handshake successful")
                return True
            else:
                logger.warning("Handshake failed")
                self.close()
                return False
                
        except socket.timeout:
            logger.error("Connection timeout")
            self._set_state(ConnectionState.ERROR)
            return False
        except ConnectionRefusedError:
            logger.error("Connection refused by receiver")
            self._set_state(ConnectionState.ERROR)
            return False
        except Exception as e:
            logger.error(f"Connection error: {e}")
            self._set_state(ConnectionState.ERROR)
            return False
            
    def _perform_handshake(self) -> bool:
        """
        Perform handshake with server.
        
        Returns:
            True if handshake successful
        """
        try:
            # Send handshake request
            self.send_raw(HANDSHAKE_REQUEST)
            
            # Wait for response
            response = self.recv_raw(len(HANDSHAKE_RESPONSE))
            
            if response == HANDSHAKE_RESPONSE:
                return True
            else:
                logger.warning(f"Unexpected handshake response: {response}")
                return False
                
        except Exception as e:
            logger.error(f"Handshake error: {e}")
            return False
            
    @property
    def server_address(self) -> Optional[Tuple[str, int]]:
        """Get server address."""
        return self._server_address


# =============================================================================
# Connection Manager for handling multiple connections
# =============================================================================

class ConnectionManager:
    """
    Manages TCP connections for the application.
    
    Provides a higher-level interface for connection handling,
    including automatic retry and connection pooling.
    """
    
    def __init__(self):
        """Initialize connection manager."""
        self._active_connections: dict[str, SecureTCPConnection] = {}
        self._lock = threading.Lock()
        
    def add_connection(self, name: str, connection: SecureTCPConnection):
        """Add a connection to the pool."""
        with self._lock:
            self._active_connections[name] = connection
            
    def get_connection(self, name: str) -> Optional[SecureTCPConnection]:
        """Get a connection by name."""
        with self._lock:
            return self._active_connections.get(name)
            
    def remove_connection(self, name: str):
        """Remove and close a connection."""
        with self._lock:
            conn = self._active_connections.pop(name, None)
            if conn:
                conn.close()
                
    def close_all(self):
        """Close all active connections."""
        with self._lock:
            for conn in self._active_connections.values():
                conn.close()
            self._active_connections.clear()


# =============================================================================
# Test / Demo
# =============================================================================

if __name__ == "__main__":
    import sys
    import time
    
    if len(sys.argv) < 2:
        print("Usage: python connection.py [server|client] [port] [host]")
        sys.exit(1)
        
    mode = sys.argv[1].lower()
    port = int(sys.argv[2]) if len(sys.argv) > 2 else DEFAULT_TCP_PORT
    
    if mode == "server":
        server = TCPServer(port=port)
        if server.start():
            print(f"Server listening on port {port}")
            print("Waiting for client...")
            
            if server.accept_connection():
                print("Client connected!")
                print(f"Client address: {server.client_address}")
                
                # Test message exchange
                server.send_message(b"Hello from server!")
                response = server.receive_message()
                print(f"Received: {response}")
                
                time.sleep(2)
                server.close()
            else:
                print("No valid client connected")
                
    elif mode == "client":
        host = sys.argv[3] if len(sys.argv) > 3 else "127.0.0.1"
        
        client = TCPClient()
        if client.connect(host, port):
            print(f"Connected to {host}:{port}")
            
            # Test message exchange
            message = client.receive_message()
            print(f"Received: {message}")
            client.send_message(b"Hello from client!")
            
            time.sleep(2)
            client.close()
        else:
            print("Failed to connect")
    else:
        print(f"Unknown mode: {mode}")
        sys.exit(1)
