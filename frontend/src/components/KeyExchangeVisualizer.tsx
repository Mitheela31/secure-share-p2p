import React, { useState, useEffect } from 'react';
import { 
  Key, 
  ArrowRight, 
  ArrowLeft, 
  Lock, 
  Unlock,
  CheckCircle2,
  Loader2,
  Shield,
  User,
  Cpu
} from 'lucide-react';
import { useCrypto } from '@/contexts/CryptoContext';
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";

interface KeyExchangeVisualizerProps {
  senderName: string;
  receiverName: string;
  onComplete: () => void;
  autoStart?: boolean;
}

type Phase = 
  | 'idle' 
  | 'sender-keygen' 
  | 'receiver-keygen' 
  | 'exchange-sender' 
  | 'exchange-receiver' 
  | 'derive-secret' 
  | 'generate-session'
  | 'complete';

const KeyExchangeVisualizer: React.FC<KeyExchangeVisualizerProps> = ({
  senderName,
  receiverName,
  onComplete,
  autoStart = true
}) => {
  const [phase, setPhase] = useState<Phase>('idle');
  const [showArrow, setShowArrow] = useState<'sender' | 'receiver' | null>(null);
  
  const { 
    senderKeyPair, 
    receiverKeyPair,
    sharedSecretDerived,
    sessionKeyGenerated,
    sharedSecret,
    sessionKey,
    generateSenderKeys,
    generateReceiverKeys,
    exchangePublicKeys,
    deriveSharedSecret,
    generateSessionKey,
    addLog
  } = useCrypto();

  useEffect(() => {
    if (autoStart && phase === 'idle') {
      startKeyExchange();
    }
  }, [autoStart]);

  const startKeyExchange = async () => {
    // Phase 1: Generate sender keys
    setPhase('sender-keygen');
    await generateSenderKeys();
    await new Promise(r => setTimeout(r, 500));

    // Phase 2: Generate receiver keys
    setPhase('receiver-keygen');
    await generateReceiverKeys();
    await new Promise(r => setTimeout(r, 500));

    // Phase 3: Exchange public keys (sender to receiver)
    setPhase('exchange-sender');
    setShowArrow('sender');
    await new Promise(r => setTimeout(r, 1000));

    // Phase 4: Exchange public keys (receiver to sender)
    setPhase('exchange-receiver');
    setShowArrow('receiver');
    await exchangePublicKeys();
    await new Promise(r => setTimeout(r, 500));
    setShowArrow(null);

    // Phase 5: Derive shared secret
    setPhase('derive-secret');
    await deriveSharedSecret();
    await new Promise(r => setTimeout(r, 500));

    // Phase 6: Generate session key
    setPhase('generate-session');
    await generateSessionKey();
    await new Promise(r => setTimeout(r, 500));

    // Complete
    setPhase('complete');
    addLog({
      type: 'success',
      category: 'key-exchange',
      message: '✓ Secure key exchange completed - Ready for encrypted file transfer',
    });
    
    setTimeout(onComplete, 1000);
  };

  const getPhaseIndex = () => {
    const phases: Phase[] = ['sender-keygen', 'receiver-keygen', 'exchange-sender', 'exchange-receiver', 'derive-secret', 'generate-session', 'complete'];
    return phases.indexOf(phase);
  };

  const isPhaseComplete = (targetPhase: Phase) => {
    const phases: Phase[] = ['sender-keygen', 'receiver-keygen', 'exchange-sender', 'exchange-receiver', 'derive-secret', 'generate-session', 'complete'];
    return phases.indexOf(phase) > phases.indexOf(targetPhase);
  };

  const isPhaseActive = (targetPhase: Phase) => phase === targetPhase;

  return (
    <TooltipProvider>
      <div className="glass-card cyber-border p-6">
        <div className="text-center mb-6">
          <h3 className="text-lg font-bold mb-1">Secure Key Exchange Protocol</h3>
          <p className="text-sm text-muted-foreground">
            Elliptic Curve Diffie-Hellman (ECDH) Key Agreement
          </p>
        </div>

        {/* Visual representation of sender and receiver */}
        <div className="flex items-center justify-between mb-8">
          {/* Sender */}
          <div className="flex flex-col items-center gap-3">
            <div className={`
              w-20 h-20 rounded-2xl flex items-center justify-center transition-all duration-300
              ${isPhaseActive('sender-keygen') ? 'bg-primary/30 animate-pulse' : 
                senderKeyPair.generated ? 'bg-success/20' : 'bg-muted'}
            `}>
              <User className={`w-10 h-10 ${senderKeyPair.generated ? 'text-success' : 'text-muted-foreground'}`} />
            </div>
            <div className="text-center">
              <p className="font-medium text-sm">{senderName}</p>
              <p className="text-xs text-muted-foreground">Sender</p>
            </div>
            
            {/* Sender key display */}
            <div className={`
              p-3 rounded-lg border transition-all duration-300 w-32
              ${senderKeyPair.generated ? 'border-success/50 bg-success/5' : 'border-border bg-muted/30'}
            `}>
              <div className="flex items-center gap-2 mb-2">
                <Key className={`w-3 h-3 ${senderKeyPair.generated ? 'text-success' : 'text-muted-foreground'}`} />
                <span className="text-xs font-medium">Keys</span>
              </div>
              {senderKeyPair.generated ? (
                <div className="space-y-1">
                  <Tooltip>
                    <TooltipTrigger asChild>
                      <p className="text-[10px] font-mono text-primary truncate cursor-help">
                        🔓 {senderKeyPair.publicKey.slice(0, 12)}...
                      </p>
                    </TooltipTrigger>
                    <TooltipContent>
                      <p className="text-xs">Public Key - Shared with receiver</p>
                    </TooltipContent>
                  </Tooltip>
                  <Tooltip>
                    <TooltipTrigger asChild>
                      <p className="text-[10px] font-mono text-muted-foreground truncate cursor-help">
                        🔐 ••••••••••••
                      </p>
                    </TooltipTrigger>
                    <TooltipContent>
                      <p className="text-xs">Private Key - Never transmitted</p>
                    </TooltipContent>
                  </Tooltip>
                </div>
              ) : (
                <p className="text-[10px] text-muted-foreground">Generating...</p>
              )}
            </div>
          </div>

          {/* Key exchange arrows */}
          <div className="flex-1 px-4 relative">
            {/* Arrow animations */}
            <div className="relative h-20 flex items-center justify-center">
              {/* Sender to receiver arrow */}
              <div className={`
                absolute inset-x-0 top-1/3 flex items-center justify-center transition-all duration-500
                ${showArrow === 'sender' ? 'opacity-100' : 'opacity-30'}
              `}>
                <div className="flex items-center gap-2 px-3 py-1 rounded-full bg-primary/20">
                  <span className="text-[10px] text-primary">Public Key</span>
                  <ArrowRight className={`w-4 h-4 text-primary ${showArrow === 'sender' ? 'animate-pulse' : ''}`} />
                </div>
              </div>

              {/* Receiver to sender arrow */}
              <div className={`
                absolute inset-x-0 bottom-1/3 flex items-center justify-center transition-all duration-500
                ${showArrow === 'receiver' ? 'opacity-100' : 'opacity-30'}
              `}>
                <div className="flex items-center gap-2 px-3 py-1 rounded-full bg-secondary/20">
                  <ArrowLeft className={`w-4 h-4 text-secondary ${showArrow === 'receiver' ? 'animate-pulse' : ''}`} />
                  <span className="text-[10px] text-secondary">Public Key</span>
                </div>
              </div>

              {/* Center status */}
              {phase === 'derive-secret' && (
                <div className="absolute inset-0 flex items-center justify-center">
                  <div className="p-3 rounded-xl bg-primary/20 border border-primary/30 animate-pulse">
                    <Cpu className="w-6 h-6 text-primary" />
                  </div>
                </div>
              )}

              {(phase === 'generate-session' || phase === 'complete') && (
                <div className="absolute inset-0 flex items-center justify-center">
                  <div className="p-3 rounded-xl bg-success/20 border border-success/30">
                    <Lock className="w-6 h-6 text-success" />
                  </div>
                </div>
              )}
            </div>
          </div>

          {/* Receiver */}
          <div className="flex flex-col items-center gap-3">
            <div className={`
              w-20 h-20 rounded-2xl flex items-center justify-center transition-all duration-300
              ${isPhaseActive('receiver-keygen') ? 'bg-secondary/30 animate-pulse' : 
                receiverKeyPair.generated ? 'bg-success/20' : 'bg-muted'}
            `}>
              <User className={`w-10 h-10 ${receiverKeyPair.generated ? 'text-success' : 'text-muted-foreground'}`} />
            </div>
            <div className="text-center">
              <p className="font-medium text-sm">{receiverName}</p>
              <p className="text-xs text-muted-foreground">Receiver</p>
            </div>
            
            {/* Receiver key display */}
            <div className={`
              p-3 rounded-lg border transition-all duration-300 w-32
              ${receiverKeyPair.generated ? 'border-success/50 bg-success/5' : 'border-border bg-muted/30'}
            `}>
              <div className="flex items-center gap-2 mb-2">
                <Key className={`w-3 h-3 ${receiverKeyPair.generated ? 'text-success' : 'text-muted-foreground'}`} />
                <span className="text-xs font-medium">Keys</span>
              </div>
              {receiverKeyPair.generated ? (
                <div className="space-y-1">
                  <Tooltip>
                    <TooltipTrigger asChild>
                      <p className="text-[10px] font-mono text-secondary truncate cursor-help">
                        🔓 {receiverKeyPair.publicKey.slice(0, 12)}...
                      </p>
                    </TooltipTrigger>
                    <TooltipContent>
                      <p className="text-xs">Public Key - Shared with sender</p>
                    </TooltipContent>
                  </Tooltip>
                  <Tooltip>
                    <TooltipTrigger asChild>
                      <p className="text-[10px] font-mono text-muted-foreground truncate cursor-help">
                        🔐 ••••••••••••
                      </p>
                    </TooltipTrigger>
                    <TooltipContent>
                      <p className="text-xs">Private Key - Never transmitted</p>
                    </TooltipContent>
                  </Tooltip>
                </div>
              ) : (
                <p className="text-[10px] text-muted-foreground">Waiting...</p>
              )}
            </div>
          </div>
        </div>

        {/* Shared secret and session key display */}
        {(sharedSecretDerived || sessionKeyGenerated) && (
          <div className="space-y-3 mb-6">
            {sharedSecretDerived && (
              <div className="p-4 rounded-xl bg-primary/10 border border-primary/30">
                <div className="flex items-center gap-2 mb-2">
                  <Unlock className="w-4 h-4 text-primary" />
                  <span className="text-sm font-medium">Shared Secret (ECDH)</span>
                </div>
                <p className="font-mono text-xs text-primary break-all">
                  {sharedSecret.slice(0, 32)}...
                </p>
                <p className="text-[10px] text-muted-foreground mt-1">
                  Independently computed by both peers
                </p>
              </div>
            )}

            {sessionKeyGenerated && (
              <div className="p-4 rounded-xl bg-success/10 border border-success/30">
                <div className="flex items-center gap-2 mb-2">
                  <Lock className="w-4 h-4 text-success" />
                  <span className="text-sm font-medium">AES-256 Session Key</span>
                </div>
                <p className="font-mono text-xs text-success break-all">
                  {sessionKey.slice(0, 32)}...
                </p>
                <p className="text-[10px] text-muted-foreground mt-1">
                  Derived using HKDF-SHA256
                </p>
              </div>
            )}
          </div>
        )}

        {/* Progress steps */}
        <div className="space-y-2">
          {[
            { phase: 'sender-keygen' as Phase, label: 'Generate Sender ECDH Keys', algorithm: 'ECDH P-256' },
            { phase: 'receiver-keygen' as Phase, label: 'Generate Receiver ECDH Keys', algorithm: 'ECDH P-256' },
            { phase: 'exchange-sender' as Phase, label: 'Exchange Public Keys', algorithm: 'P2P Secure Channel' },
            { phase: 'derive-secret' as Phase, label: 'Derive Shared Secret', algorithm: 'ECDH' },
            { phase: 'generate-session' as Phase, label: 'Generate Session Key', algorithm: 'AES-256-GCM' },
          ].map((step, index) => (
            <div
              key={step.phase}
              className={`
                flex items-center gap-3 p-2 rounded-lg transition-all
                ${isPhaseActive(step.phase) || (step.phase === 'exchange-sender' && phase === 'exchange-receiver')
                  ? 'bg-primary/10 border border-primary/30' 
                  : ''}
              `}
            >
              {isPhaseComplete(step.phase) || (step.phase === 'exchange-sender' && isPhaseComplete('exchange-receiver')) ? (
                <CheckCircle2 className="w-4 h-4 text-success shrink-0" />
              ) : isPhaseActive(step.phase) || (step.phase === 'exchange-sender' && phase === 'exchange-receiver') ? (
                <Loader2 className="w-4 h-4 text-primary animate-spin shrink-0" />
              ) : (
                <div className="w-4 h-4 rounded-full border-2 border-muted shrink-0" />
              )}
              <span className={`text-sm flex-1 ${
                isPhaseActive(step.phase) ? 'text-foreground font-medium' : 
                isPhaseComplete(step.phase) ? 'text-muted-foreground' : 'text-muted-foreground'
              }`}>
                {step.label}
              </span>
              <span className="text-[10px] px-2 py-0.5 rounded bg-muted text-muted-foreground font-mono">
                {step.algorithm}
              </span>
            </div>
          ))}
        </div>

        {phase === 'complete' && (
          <div className="mt-6 p-4 rounded-xl bg-success/10 border border-success/30 text-center">
            <Shield className="w-8 h-8 text-success mx-auto mb-2" />
            <p className="font-medium text-success">Secure Channel Established!</p>
            <p className="text-xs text-muted-foreground mt-1">
              End-to-end encryption ready for file transfer
            </p>
          </div>
        )}
      </div>
    </TooltipProvider>
  );
};

export default KeyExchangeVisualizer;
