# Secure P2P File Transfer

LAN-based peer-to-peer secure file sharing with end-to-end encryption.

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                     SECURE P2P FILE TRANSFER ARCHITECTURE                    │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   SENDER                              RECEIVER                              │
│   ┌─────────────┐                     ┌─────────────┐                       │
│   │ main_sender │                     │main_receiver│                       │
│   └──────┬──────┘                     └──────┬──────┘                       │
│          │                                   │                              │
│          ▼                                   ▼                              │
│   ┌─────────────┐    UDP Broadcast    ┌─────────────┐                       │
│   │  discovery  │◄────────────────────│  discovery  │                       │
│   │  (Listener) │    SECURE_SHARE:    │(Broadcaster)│                       │
│   └──────┬──────┘     <tcp_port>      └──────┬──────┘                       │
│          │                                   │                              │
│          │           TCP Handshake           │                              │
│          └─────────────────┬─────────────────┘                              │
│                            │                                                │
│                            ▼                                                │
│                    ┌─────────────┐                                          │
│                    │ connection  │                                          │
│                    │(TCP Client/ │                                          │
│                    │   Server)   │                                          │
│                    └──────┬──────┘                                          │
│                           │                                                 │
│                           ▼                                                 │
│                    ┌─────────────┐                                          │
│                    │crypto_utils │                                          │
│                    │   (ECDH +   │                                          │
│                    │HKDF + AES)  │                                          │
│                    └──────┬──────┘                                          │
│                           │                                                 │
│                           ▼                                                 │
│                    ┌─────────────┐                                          │
│                    │file_transfer│                                          │
│                    │ (Encrypted  │                                          │
│                    │  Send/Recv) │                                          │
│                    └─────────────┘                                          │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Protocol Flow

### Phase 1: UDP Discovery

```
Receiver                                         Sender
   │                                               │
   │    UDP Broadcast (255.255.255.255:9999)      │
   │  ─────────────────────────────────────────►  │
   │         "SECURE_SHARE:5000"                  │
   │                                               │
   │    (Broadcast repeats every 3 seconds)       │
   │  ─────────────────────────────────────────►  │
   │                                               │
```

### Phase 2: TCP Connection + Handshake

```
Receiver                                         Sender
   │                                               │
   │           TCP Connect (port 5000)             │
   │  ◄─────────────────────────────────────────  │
   │                                               │
   │         "SECURE_SHARE_HANDSHAKE"              │
   │  ◄─────────────────────────────────────────  │
   │                                               │
   │          "HANDSHAKE_ACCEPTED"                 │
   │  ─────────────────────────────────────────►  │
   │                                               │
```

### Phase 3: ECDH Key Exchange

```
Receiver                                         Sender
   │                                               │
   │    Generate ECDH Key Pair (SECP256R1)        │
   │    Generate ECDH Key Pair (SECP256R1)        │
   │                                               │
   │           Sender Public Key                   │
   │  ◄─────────────────────────────────────────  │
   │                                               │
   │           Receiver Public Key                 │
   │  ─────────────────────────────────────────►  │
   │                                               │
   │    Derive Shared Secret (ECDH)               │
   │    Derive Shared Secret (ECDH)               │
   │                                               │
   │    Derive AES-256 Key (HKDF-SHA256)          │
   │    Derive AES-256 Key (HKDF-SHA256)          │
   │                                               │
   │    Both parties now have identical key!       │
```

### Phase 4: Encrypted File Transfer

```
Receiver                                         Sender
   │                                               │
   │                                    Read file  │
   │                                    Encrypt    │
   │                                    (AES-GCM)  │
   │                                               │
   │           FILE_METADATA (JSON)                │
   │  ◄─────────────────────────────────────────  │
   │           {filename, size, checksum}         │
   │                                               │
   │           FILE_DATA                           │
   │  ◄─────────────────────────────────────────  │
   │           [IV][TAG][LENGTH][CIPHERTEXT]      │
   │                                               │
   │    Decrypt (AES-GCM)                         │
   │    Verify checksum                            │
   │    Save file                                  │
   │                                               │
   │           TRANSFER_COMPLETE                   │
   │  ─────────────────────────────────────────►  │
   │                                               │
```

## Cryptographic Details

### Key Exchange: ECDH (Elliptic Curve Diffie-Hellman)

| Parameter | Value |
|-----------|-------|
| Curve | SECP256R1 (NIST P-256) |
| Key Size | 256 bits |
| Public Key Format | X962 Compressed Point |

### Key Derivation: HKDF (HMAC-based Key Derivation Function)

| Parameter | Value |
|-----------|-------|
| Hash | SHA-256 |
| Output Length | 32 bytes (256 bits) |
| Info | "secure-p2p-file-transfer" |

### Encryption: AES-256-GCM (Galois/Counter Mode)

| Parameter | Value |
|-----------|-------|
| Key Size | 256 bits (32 bytes) |
| IV Size | 96 bits (12 bytes) |
| Tag Size | 128 bits (16 bytes) |

## Security Properties

| Property | Provided By | Description |
|----------|-------------|-------------|
| **Confidentiality** | AES-256-GCM | Data is encrypted, unreadable without key |
| **Integrity** | GCM Tag | Tampering is detected |
| **Authentication** | GCM Tag | Data origin is verified |
| **Forward Secrecy** | Ephemeral ECDH | Each session uses new keys |
| **Key Agreement** | ECDH | No key transmission required |

## File Structure

```
p2p/
├── discovery.py       # UDP broadcast/listen for device discovery
├── connection.py      # TCP server/client with handshake
├── crypto_utils.py    # ECDH + HKDF + AES-GCM implementations
├── file_transfer.py   # Encrypted file send/receive logic
├── main_sender.py     # Sender application (interactive console)
├── main_receiver.py   # Receiver application (interactive console)
├── requirements.txt   # Python dependencies
└── README.md          # This file
```

## Installation

```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

## Usage

### Start Receiver (on one machine)

```bash
python main_receiver.py

# Or with options:
python main_receiver.py --port 5000 --directory ./received_files
```

### Start Sender (on another machine in same LAN)

```bash
python main_sender.py
```

### Test Locally (same machine)

Terminal 1:
```bash
python main_receiver.py
```

Terminal 2:
```bash
python main_sender.py
```

## Building Executables

### Windows (.exe)

```bash
# Install PyInstaller
pip install pyinstaller

# Build sender
pyinstaller --onefile --name SecureSender main_sender.py

# Build receiver
pyinstaller --onefile --name SecureReceiver main_receiver.py

# Executables will be in dist/ folder
```

### Linux/Mac

```bash
pyinstaller --onefile --name SecureSender main_sender.py
pyinstaller --onefile --name SecureReceiver main_receiver.py
```

## Security Checklist

### ✅ Implemented

- [x] Real ECDH key exchange (no hardcoded keys)
- [x] AES-256-GCM authenticated encryption
- [x] Unique IV per encryption
- [x] HKDF for key derivation
- [x] Checksum verification (SHA-256)
- [x] Memory clearing for sensitive data
- [x] Proper exception handling
- [x] Socket cleanup on errors
- [x] Handshake validation

### ❌ Not Implemented (Requirements Met)

- [x] No hardcoded keys anywhere
- [x] No plaintext key logging
- [x] No plaintext file storage during transfer
- [x] No insecure encryption modes (CBC, ECB, etc.)
- [x] No mock implementations

## Troubleshooting

### Receiver not discovered

1. Ensure both devices are on the same LAN
2. Check firewall allows UDP port 9999
3. Check firewall allows TCP port 5000 (or configured port)
4. Try using IP address directly

### Connection refused

1. Make sure receiver is running before sender tries to connect
2. Check TCP port is not in use by another application
3. Check firewall settings

### Decryption failed

1. This indicates data tampering or corruption
2. Try again - network issues may have caused data loss
3. Ensure no proxy/firewall is inspecting traffic

## Network Requirements

| Port | Protocol | Direction | Purpose |
|------|----------|-----------|---------|
| 9999 | UDP | Broadcast | Device discovery |
| 5000 | TCP | Inbound | File transfer (configurable) |

## License

This implementation is for educational purposes. Use at your own risk.

## References

- [ECDH (Wikipedia)](https://en.wikipedia.org/wiki/Elliptic-curve_Diffie%E2%80%93Hellman)
- [HKDF RFC 5869](https://tools.ietf.org/html/rfc5869)
- [AES-GCM NIST SP 800-38D](https://csrc.nist.gov/publications/detail/sp/800-38d/final)
- [Python cryptography library](https://cryptography.io/)
