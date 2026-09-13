import React, { useEffect, useRef } from 'react';
import { 
  Terminal, 
  Key, 
  Lock, 
  Unlock, 
  Send, 
  Shield, 
  Wifi,
  CheckCircle2,
  AlertTriangle,
  Info,
  X
} from 'lucide-react';
import { useCrypto, SecurityLogEntry } from '@/contexts/CryptoContext';
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";

interface SecurityLogProps {
  maxHeight?: string;
  showClear?: boolean;
  compact?: boolean;
}

const SecurityLog: React.FC<SecurityLogProps> = ({ 
  maxHeight = '300px', 
  showClear = true,
  compact = false 
}) => {
  const { logs, clearLogs } = useCrypto();
  const scrollRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom when new logs are added
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [logs]);

  const getIcon = (entry: SecurityLogEntry) => {
    switch (entry.category) {
      case 'key-gen':
        return <Key className="w-3.5 h-3.5" />;
      case 'key-exchange':
        return <Unlock className="w-3.5 h-3.5" />;
      case 'encryption':
        return <Lock className="w-3.5 h-3.5" />;
      case 'decryption':
        return <Unlock className="w-3.5 h-3.5" />;
      case 'connection':
        return <Wifi className="w-3.5 h-3.5" />;
      case 'transfer':
        return <Send className="w-3.5 h-3.5" />;
      case 'auth':
        return <Shield className="w-3.5 h-3.5" />;
      default:
        return <Info className="w-3.5 h-3.5" />;
    }
  };

  const getTypeStyles = (type: SecurityLogEntry['type']) => {
    switch (type) {
      case 'success':
        return 'text-success';
      case 'warning':
        return 'text-warning';
      case 'error':
        return 'text-destructive';
      case 'crypto':
        return 'text-primary';
      case 'network':
        return 'text-secondary';
      default:
        return 'text-muted-foreground';
    }
  };

  const getTypeIcon = (type: SecurityLogEntry['type']) => {
    switch (type) {
      case 'success':
        return <CheckCircle2 className="w-3 h-3 text-success" />;
      case 'warning':
        return <AlertTriangle className="w-3 h-3 text-warning" />;
      case 'error':
        return <X className="w-3 h-3 text-destructive" />;
      default:
        return null;
    }
  };

  const formatTimestamp = (date: Date) => {
    const time = date.toLocaleTimeString('en-US', { 
      hour12: false, 
      hour: '2-digit', 
      minute: '2-digit', 
      second: '2-digit',
    });
    const ms = date.getMilliseconds().toString().padStart(3, '0');
    return `${time}.${ms}`;
  };

  const getCategoryTooltip = (category: SecurityLogEntry['category']) => {
    switch (category) {
      case 'key-gen':
        return 'Key Generation: Creating cryptographic key pairs using elliptic curve cryptography';
      case 'key-exchange':
        return 'Key Exchange: Securely sharing public keys between peers using ECDH protocol';
      case 'encryption':
        return 'Encryption: Converting plaintext data into ciphertext using AES-256-GCM';
      case 'decryption':
        return 'Decryption: Converting ciphertext back to plaintext using the session key';
      case 'connection':
        return 'Connection: Establishing P2P connection between sender and receiver';
      case 'transfer':
        return 'Transfer: Securely transmitting encrypted file chunks over the network';
      case 'auth':
        return 'Authentication: Verifying user identity and session integrity';
      default:
        return 'System log entry';
    }
  };

  if (logs.length === 0 && compact) {
    return null;
  }

  return (
    <div className="glass-card cyber-border overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-border bg-muted/30">
        <div className="flex items-center gap-2">
          <Terminal className="w-4 h-4 text-primary" />
          <span className="font-bold text-sm">Security Console</span>
          {logs.length > 0 && (
            <span className="px-1.5 py-0.5 rounded-full bg-primary/20 text-primary text-xs font-mono">
              {logs.length}
            </span>
          )}
        </div>
        {showClear && logs.length > 0 && (
          <button
            onClick={clearLogs}
            className="p-1 rounded hover:bg-muted transition-colors"
            title="Clear logs"
          >
            <X className="w-4 h-4 text-muted-foreground" />
          </button>
        )}
      </div>

      {/* Log entries */}
      <div 
        ref={scrollRef}
        className="overflow-y-auto font-mono text-xs"
        style={{ maxHeight }}
      >
        {logs.length === 0 ? (
          <div className="p-6 text-center text-muted-foreground">
            <Terminal className="w-8 h-8 mx-auto mb-2 opacity-50" />
            <p>Waiting for cryptographic operations...</p>
          </div>
        ) : (
          <div className="divide-y divide-border/50">
            <TooltipProvider>
              {logs.map((entry) => (
                <div
                  key={entry.id}
                  className="px-3 py-2 hover:bg-muted/30 transition-colors animate-fade-in-up"
                >
                  <div className="flex items-start gap-2">
                    {/* Timestamp */}
                    <span className="text-muted-foreground shrink-0 tabular-nums">
                      [{formatTimestamp(entry.timestamp)}]
                    </span>

                    {/* Category icon with tooltip */}
                    <Tooltip>
                      <TooltipTrigger asChild>
                        <span className={`shrink-0 ${getTypeStyles(entry.type)}`}>
                          {getIcon(entry)}
                        </span>
                      </TooltipTrigger>
                      <TooltipContent side="right" className="max-w-xs">
                        <p className="text-xs">{getCategoryTooltip(entry.category)}</p>
                      </TooltipContent>
                    </Tooltip>

                    {/* Message */}
                    <span className={`flex-1 ${getTypeStyles(entry.type)}`}>
                      {entry.message}
                    </span>

                    {/* Type indicator */}
                    {getTypeIcon(entry.type)}

                    {/* Algorithm badge */}
                    {entry.algorithm && (
                      <Tooltip>
                        <TooltipTrigger asChild>
                          <span className="shrink-0 px-1.5 py-0.5 rounded bg-primary/20 text-primary text-[10px]">
                            {entry.algorithm}
                          </span>
                        </TooltipTrigger>
                        <TooltipContent side="left" className="max-w-xs">
                          <p className="text-xs font-medium mb-1">{entry.algorithm}</p>
                          <p className="text-xs text-muted-foreground">
                            {entry.algorithm.includes('ECDH') && 
                              'Elliptic Curve Diffie-Hellman: A key exchange protocol that allows two parties to establish a shared secret over an insecure channel.'}
                            {entry.algorithm.includes('AES-256') && 
                              'Advanced Encryption Standard with 256-bit key: Military-grade symmetric encryption used to protect classified information.'}
                            {entry.algorithm.includes('HKDF') && 
                              'HMAC-based Key Derivation Function: Derives cryptographically strong keys from a shared secret.'}
                            {entry.algorithm.includes('SHA-256') && 
                              'Secure Hash Algorithm: Produces a 256-bit hash value, used for integrity verification.'}
                          </p>
                        </TooltipContent>
                      </Tooltip>
                    )}
                  </div>
                </div>
              ))}
            </TooltipProvider>
          </div>
        )}
      </div>

      {/* Status bar */}
      <div className="px-4 py-2 border-t border-border bg-muted/30 flex items-center justify-between text-xs">
        <div className="flex items-center gap-2">
          <div className="w-2 h-2 rounded-full bg-success pulse-dot" />
          <span className="text-muted-foreground">Secure channel active</span>
        </div>
        <span className="text-muted-foreground">E2E Encrypted</span>
      </div>
    </div>
  );
};

export default SecurityLog;
