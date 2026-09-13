import React, { createContext, useContext, useState, useCallback, ReactNode } from 'react';

export interface SecurityLogEntry {
  id: string;
  timestamp: Date;
  type: 'info' | 'success' | 'warning' | 'crypto' | 'network' | 'error';
  category: 'key-gen' | 'key-exchange' | 'encryption' | 'decryption' | 'connection' | 'transfer' | 'auth';
  message: string;
  algorithm?: string;
}

export interface KeyPair {
  publicKey: string;
  privateKey: string;
  generated: boolean;
}

export interface CryptoState {
  // Key pairs
  senderKeyPair: KeyPair;
  receiverKeyPair: KeyPair;
  
  // Shared secret and session key
  sharedSecretDerived: boolean;
  sessionKeyGenerated: boolean;
  sharedSecret: string;
  sessionKey: string;
  
  // Connection state
  connectionEstablished: boolean;
  secureChannelActive: boolean;
  
  // Transfer state
  currentChunk: number;
  totalChunks: number;
  transferPhase: 'idle' | 'key-exchange' | 'encrypting' | 'transmitting' | 'decrypting' | 'complete';
  
  // Security logs
  logs: SecurityLogEntry[];
}

interface CryptoContextType extends CryptoState {
  addLog: (entry: Omit<SecurityLogEntry, 'id' | 'timestamp'>) => void;
  clearLogs: () => void;
  generateSenderKeys: () => Promise<void>;
  generateReceiverKeys: () => Promise<void>;
  exchangePublicKeys: () => Promise<void>;
  deriveSharedSecret: () => Promise<void>;
  generateSessionKey: () => Promise<void>;
  setTransferPhase: (phase: CryptoState['transferPhase']) => void;
  setChunkProgress: (current: number, total: number) => void;
  setConnectionEstablished: (established: boolean) => void;
  setSecureChannelActive: (active: boolean) => void;
  resetCryptoState: () => void;
}

const initialState: CryptoState = {
  senderKeyPair: { publicKey: '', privateKey: '', generated: false },
  receiverKeyPair: { publicKey: '', privateKey: '', generated: false },
  sharedSecretDerived: false,
  sessionKeyGenerated: false,
  sharedSecret: '',
  sessionKey: '',
  connectionEstablished: false,
  secureChannelActive: false,
  currentChunk: 0,
  totalChunks: 5,
  transferPhase: 'idle',
  logs: [],
};

const CryptoContext = createContext<CryptoContextType | undefined>(undefined);

// Simulate key generation (mock cryptographic values)
const generateMockKeyPair = () => {
  const chars = '0123456789abcdef';
  const generateHex = (length: number) => 
    Array.from({ length }, () => chars[Math.floor(Math.random() * chars.length)]).join('');
  
  return {
    publicKey: `04${generateHex(128)}`, // Simulated ECDH public key
    privateKey: generateHex(64), // Simulated private key
  };
};

const generateMockSecret = () => {
  const chars = '0123456789abcdef';
  return Array.from({ length: 64 }, () => chars[Math.floor(Math.random() * chars.length)]).join('');
};

export const CryptoProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  const [state, setState] = useState<CryptoState>(initialState);

  const addLog = useCallback((entry: Omit<SecurityLogEntry, 'id' | 'timestamp'>) => {
    const newEntry: SecurityLogEntry = {
      ...entry,
      id: `log-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
      timestamp: new Date(),
    };
    setState(prev => ({
      ...prev,
      logs: [...prev.logs, newEntry],
    }));
  }, []);

  const clearLogs = useCallback(() => {
    setState(prev => ({ ...prev, logs: [] }));
  }, []);

  const generateSenderKeys = useCallback(async () => {
    addLog({
      type: 'crypto',
      category: 'key-gen',
      message: 'Initiating ECDH key pair generation for Sender...',
      algorithm: 'ECDH P-256',
    });

    await new Promise(r => setTimeout(r, 800));

    const keyPair = generateMockKeyPair();
    setState(prev => ({
      ...prev,
      senderKeyPair: { ...keyPair, generated: true },
    }));

    addLog({
      type: 'success',
      category: 'key-gen',
      message: `Sender public key generated: ${keyPair.publicKey.slice(0, 20)}...`,
      algorithm: 'ECDH P-256',
    });

    addLog({
      type: 'info',
      category: 'key-gen',
      message: '🔒 Private key stored securely (never leaves device)',
    });
  }, [addLog]);

  const generateReceiverKeys = useCallback(async () => {
    addLog({
      type: 'crypto',
      category: 'key-gen',
      message: 'Initiating ECDH key pair generation for Receiver...',
      algorithm: 'ECDH P-256',
    });

    await new Promise(r => setTimeout(r, 800));

    const keyPair = generateMockKeyPair();
    setState(prev => ({
      ...prev,
      receiverKeyPair: { ...keyPair, generated: true },
    }));

    addLog({
      type: 'success',
      category: 'key-gen',
      message: `Receiver public key generated: ${keyPair.publicKey.slice(0, 20)}...`,
      algorithm: 'ECDH P-256',
    });

    addLog({
      type: 'info',
      category: 'key-gen',
      message: '🔒 Private key stored securely (never leaves device)',
    });
  }, [addLog]);

  const exchangePublicKeys = useCallback(async () => {
    addLog({
      type: 'network',
      category: 'key-exchange',
      message: '📤 Sender transmitting public key to Receiver...',
    });

    await new Promise(r => setTimeout(r, 600));

    addLog({
      type: 'success',
      category: 'key-exchange',
      message: '✓ Sender public key received by Receiver',
    });

    await new Promise(r => setTimeout(r, 400));

    addLog({
      type: 'network',
      category: 'key-exchange',
      message: '📤 Receiver transmitting public key to Sender...',
    });

    await new Promise(r => setTimeout(r, 600));

    addLog({
      type: 'success',
      category: 'key-exchange',
      message: '✓ Receiver public key received by Sender',
    });

    addLog({
      type: 'info',
      category: 'key-exchange',
      message: '🔐 Public keys exchanged securely over P2P channel',
    });
  }, [addLog]);

  const deriveSharedSecret = useCallback(async () => {
    addLog({
      type: 'crypto',
      category: 'key-exchange',
      message: 'Deriving shared secret using ECDH...',
      algorithm: 'ECDH',
    });

    await new Promise(r => setTimeout(r, 1000));

    const secret = generateMockSecret();
    setState(prev => ({
      ...prev,
      sharedSecret: secret,
      sharedSecretDerived: true,
    }));

    addLog({
      type: 'success',
      category: 'key-exchange',
      message: `Shared secret derived: ${secret.slice(0, 16)}...`,
      algorithm: 'ECDH',
    });

    addLog({
      type: 'info',
      category: 'key-exchange',
      message: '✓ Both peers independently computed identical shared secret',
    });
  }, [addLog]);

  const generateSessionKey = useCallback(async () => {
    addLog({
      type: 'crypto',
      category: 'encryption',
      message: 'Deriving AES-256 session key from shared secret...',
      algorithm: 'HKDF-SHA256',
    });

    await new Promise(r => setTimeout(r, 600));

    const sessionKey = generateMockSecret().slice(0, 64);
    setState(prev => ({
      ...prev,
      sessionKey,
      sessionKeyGenerated: true,
    }));

    addLog({
      type: 'success',
      category: 'encryption',
      message: `AES-256 session key generated: ${sessionKey.slice(0, 16)}...`,
      algorithm: 'AES-256-GCM',
    });

    addLog({
      type: 'info',
      category: 'encryption',
      message: '🔐 Symmetric encryption ready for file transfer',
    });
  }, [addLog]);

  const setTransferPhase = useCallback((phase: CryptoState['transferPhase']) => {
    setState(prev => ({ ...prev, transferPhase: phase }));
  }, []);

  const setChunkProgress = useCallback((current: number, total: number) => {
    setState(prev => ({ ...prev, currentChunk: current, totalChunks: total }));
  }, []);

  const setConnectionEstablished = useCallback((established: boolean) => {
    setState(prev => ({ ...prev, connectionEstablished: established }));
  }, []);

  const setSecureChannelActive = useCallback((active: boolean) => {
    setState(prev => ({ ...prev, secureChannelActive: active }));
  }, []);

  const resetCryptoState = useCallback(() => {
    setState(initialState);
  }, []);

  return (
    <CryptoContext.Provider
      value={{
        ...state,
        addLog,
        clearLogs,
        generateSenderKeys,
        generateReceiverKeys,
        exchangePublicKeys,
        deriveSharedSecret,
        generateSessionKey,
        setTransferPhase,
        setChunkProgress,
        setConnectionEstablished,
        setSecureChannelActive,
        resetCryptoState,
      }}
    >
      {children}
    </CryptoContext.Provider>
  );
};

export const useCrypto = () => {
  const context = useContext(CryptoContext);
  if (!context) {
    throw new Error('useCrypto must be used within a CryptoProvider');
  }
  return context;
};
