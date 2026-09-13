import React, { useState } from 'react';
import { 
  Download, 
  Lock, 
  CheckCircle2, 
  Loader2,
  FileCheck,
  Shield,
  Unlock,
  Package
} from 'lucide-react';
import { useCrypto } from '@/contexts/CryptoContext';
import ChunkProgress from './ChunkProgress';
import PacketFlowAnimation from './PacketFlowAnimation';
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";

interface FileReceiveProps {
  senderName: string;
  fileName: string;
  fileSize: string;
  onReceiveComplete: () => void;
}

type ReceiveStatus = 'pending' | 'receiving' | 'decrypting' | 'verifying' | 'complete';

const TOTAL_CHUNKS = 5;

const FileReceive: React.FC<FileReceiveProps> = ({ 
  senderName, 
  fileName, 
  fileSize,
  onReceiveComplete 
}) => {
  const [status, setStatus] = useState<ReceiveStatus>('pending');
  const [progress, setProgress] = useState(0);
  const [currentChunk, setCurrentChunk] = useState(0);

  const { addLog, setTransferPhase, setChunkProgress } = useCrypto();

  const simulateReceive = async () => {
    addLog({
      type: 'info',
      category: 'transfer',
      message: `Starting to receive encrypted file: ${fileName} from ${senderName}`,
    });

    // Phase 1: Receiving encrypted chunks
    setStatus('receiving');
    setTransferPhase('transmitting');
    setProgress(0);

    for (let chunk = 1; chunk <= TOTAL_CHUNKS; chunk++) {
      setCurrentChunk(chunk);
      setChunkProgress(chunk, TOTAL_CHUNKS);
      
      addLog({
        type: 'network',
        category: 'transfer',
        message: `Receiving encrypted chunk ${chunk}/${TOTAL_CHUNKS}...`,
      });

      for (let i = 0; i < 10; i++) {
        await new Promise(r => setTimeout(r, 50));
        const receiveProgress = ((chunk - 1) / TOTAL_CHUNKS) * 40 + (i / 10) * (40 / TOTAL_CHUNKS);
        setProgress(Math.round(receiveProgress));
      }

      addLog({
        type: 'success',
        category: 'transfer',
        message: `Chunk ${chunk}/${TOTAL_CHUNKS} received successfully`,
      });
    }

    addLog({
      type: 'success',
      category: 'transfer',
      message: '✓ All encrypted chunks received',
    });

    // Phase 2: Decrypting chunks
    setStatus('decrypting');
    setTransferPhase('decrypting');
    setCurrentChunk(0);

    addLog({
      type: 'crypto',
      category: 'decryption',
      message: 'Starting decryption with session key...',
      algorithm: 'AES-256-GCM',
    });

    for (let chunk = 1; chunk <= TOTAL_CHUNKS; chunk++) {
      setCurrentChunk(chunk);
      setChunkProgress(chunk, TOTAL_CHUNKS);

      addLog({
        type: 'crypto',
        category: 'decryption',
        message: `Decrypting chunk ${chunk}/${TOTAL_CHUNKS}...`,
        algorithm: 'AES-256-GCM',
      });

      for (let i = 0; i < 10; i++) {
        await new Promise(r => setTimeout(r, 60));
        const decryptProgress = 40 + ((chunk - 1) / TOTAL_CHUNKS) * 40 + (i / 10) * (40 / TOTAL_CHUNKS);
        setProgress(Math.round(decryptProgress));
      }

      addLog({
        type: 'success',
        category: 'decryption',
        message: `Chunk ${chunk}/${TOTAL_CHUNKS} decrypted successfully`,
      });
    }

    addLog({
      type: 'success',
      category: 'decryption',
      message: '✓ All chunks decrypted successfully',
      algorithm: 'AES-256-GCM',
    });

    // Phase 3: Verifying integrity
    setStatus('verifying');

    addLog({
      type: 'crypto',
      category: 'decryption',
      message: 'Verifying file integrity...',
      algorithm: 'GCM Auth Tag',
    });

    for (let i = 80; i <= 100; i++) {
      await new Promise(r => setTimeout(r, 30));
      setProgress(i);
    }

    addLog({
      type: 'success',
      category: 'decryption',
      message: '✓ File integrity verified - Authentication tag valid',
    });

    // Complete
    setStatus('complete');
    setTransferPhase('complete');

    addLog({
      type: 'success',
      category: 'transfer',
      message: `File "${fileName}" received and decrypted successfully`,
    });

    addLog({
      type: 'info',
      category: 'transfer',
      message: '🔒 File stored securely on device',
    });

    setTimeout(onReceiveComplete, 1500);
  };

  const getStatusInfo = () => {
    switch (status) {
      case 'receiving':
        return { 
          text: 'Receiving encrypted chunks...', 
          icon: Download,
          color: 'text-secondary',
          bgColor: 'bg-secondary/20'
        };
      case 'decrypting':
        return { 
          text: 'Decrypting with session key...', 
          icon: Unlock,
          color: 'text-primary',
          bgColor: 'bg-primary/20'
        };
      case 'verifying':
        return { 
          text: 'Verifying file integrity...', 
          icon: Shield,
          color: 'text-warning',
          bgColor: 'bg-warning/20'
        };
      case 'complete':
        return { 
          text: 'File received successfully!', 
          icon: CheckCircle2,
          color: 'text-success',
          bgColor: 'bg-success/20'
        };
      default:
        return null;
    }
  };

  const statusInfo = getStatusInfo();

  if (status === 'pending') {
    return (
      <TooltipProvider>
        <div className="glass-card cyber-border animated-border p-6">
          {/* Incoming notification */}
          <div className="flex items-center gap-3 mb-6">
            <div className="w-3 h-3 rounded-full bg-secondary pulse-dot" />
            <span className="text-secondary font-medium">Encrypted file incoming</span>
          </div>

          <div className="flex items-start gap-4 mb-6">
            <div className="w-14 h-14 rounded-xl bg-primary/20 flex items-center justify-center animate-encrypt">
              <Lock className="w-7 h-7 text-primary" />
            </div>
            <div className="flex-1">
              <h3 className="font-bold text-lg">{fileName}</h3>
              <p className="text-muted-foreground text-sm">{fileSize}</p>
              <p className="text-muted-foreground text-sm mt-1">
                From: <span className="text-primary">{senderName}</span>
              </p>
            </div>
          </div>

          {/* Security badges */}
          <div className="flex flex-wrap gap-2 mb-6">
            <Tooltip>
              <TooltipTrigger asChild>
                <div className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-success/10 text-success text-xs cursor-help">
                  <Shield className="w-3 h-3" />
                  <span>End-to-End Encrypted</span>
                </div>
              </TooltipTrigger>
              <TooltipContent>
                <p className="text-xs">File was encrypted on sender's device and only you can decrypt it</p>
              </TooltipContent>
            </Tooltip>
            <Tooltip>
              <TooltipTrigger asChild>
                <div className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-primary/10 text-primary text-xs cursor-help">
                  <Lock className="w-3 h-3" />
                  <span>AES-256-GCM</span>
                </div>
              </TooltipTrigger>
              <TooltipContent>
                <p className="text-xs">Military-grade encryption with authentication</p>
              </TooltipContent>
            </Tooltip>
            <Tooltip>
              <TooltipTrigger asChild>
                <div className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-secondary/10 text-secondary text-xs cursor-help">
                  <Package className="w-3 h-3" />
                  <span>{TOTAL_CHUNKS} Chunks</span>
                </div>
              </TooltipTrigger>
              <TooltipContent>
                <p className="text-xs">File is split into {TOTAL_CHUNKS} encrypted chunks for secure transmission</p>
              </TooltipContent>
            </Tooltip>
          </div>

          <button
            onClick={simulateReceive}
            className="w-full py-4 cyber-btn-secondary text-secondary-foreground font-semibold rounded-xl flex items-center justify-center gap-2"
          >
            <Download className="w-5 h-5" />
            <span>Receive & Decrypt File</span>
          </button>
        </div>
      </TooltipProvider>
    );
  }

  return (
    <TooltipProvider>
      <div className="glass-card cyber-border p-6">
        {/* Status header */}
        <div className="text-center mb-6">
          <div className={`
            inline-flex items-center justify-center w-16 h-16 rounded-2xl mb-4
            ${statusInfo?.bgColor}
          `}>
            {statusInfo && (
              <statusInfo.icon className={`
                w-8 h-8 ${statusInfo.color}
                ${status !== 'complete' ? 'animate-pulse' : ''}
              `} />
            )}
          </div>
          <p className={`font-medium ${statusInfo?.color}`}>
            {statusInfo?.text}
          </p>
          <p className="text-sm text-muted-foreground mt-1">{fileName}</p>
        </div>

        {/* Packet flow animation for receiving */}
        {status === 'receiving' && (
          <PacketFlowAnimation
            isActive={true}
            senderName={senderName}
            receiverName="You"
          />
        )}

        {/* Chunk progress */}
        {(status === 'receiving' || status === 'decrypting') && (
          <ChunkProgress
            currentChunk={currentChunk}
            totalChunks={TOTAL_CHUNKS}
            phase={status === 'receiving' ? 'transmitting' : 'decrypting'}
          />
        )}

        {/* Overall progress */}
        <div className="space-y-2 mt-6 mb-6">
          <div className="flex justify-between text-sm">
            <span className="text-muted-foreground">Overall Progress</span>
            <span className="font-mono text-secondary">{progress}%</span>
          </div>
          <div className="cyber-progress">
            <div 
              className="cyber-progress-bar"
              style={{ width: `${progress}%` }}
            />
          </div>
        </div>

        {/* Status steps */}
        <div className="space-y-2">
          {[
            { key: 'receiving', label: 'Receiving encrypted chunks', algorithm: 'P2P Channel' },
            { key: 'decrypting', label: 'Decrypting file chunks', algorithm: 'AES-256-GCM' },
            { key: 'verifying', label: 'Verifying integrity', algorithm: 'GCM Auth' },
            { key: 'complete', label: 'File stored securely', algorithm: 'Complete' },
          ].map((step, index) => {
            const isActive = status === step.key;
            const statusOrder = ['receiving', 'decrypting', 'verifying', 'complete'];
            const isPast = statusOrder.indexOf(status) > index;
            
            return (
              <div
                key={step.key}
                className={`
                  flex items-center gap-3 p-3 rounded-lg transition-all
                  ${isActive ? 'bg-secondary/10 border border-secondary/30' : ''}
                `}
              >
                {isPast ? (
                  <CheckCircle2 className="w-5 h-5 text-success" />
                ) : isActive ? (
                  <Loader2 className="w-5 h-5 text-secondary animate-spin" />
                ) : (
                  <div className="w-5 h-5 rounded-full border-2 border-muted" />
                )}
                <span className={`flex-1 ${isActive ? 'text-foreground font-medium' : 'text-muted-foreground'}`}>
                  {step.label}
                </span>
                <span className="text-[10px] px-2 py-0.5 rounded bg-muted text-muted-foreground font-mono">
                  {step.algorithm}
                </span>
              </div>
            );
          })}
        </div>

        {status === 'complete' && (
          <div className="mt-6 p-4 rounded-xl bg-success/10 border border-success/30 flex items-center gap-3">
            <FileCheck className="w-6 h-6 text-success" />
            <div>
              <p className="font-medium text-success">File received and decrypted</p>
              <p className="text-sm text-muted-foreground">
                Integrity verified • Stored securely on your device
              </p>
            </div>
          </div>
        )}
      </div>
    </TooltipProvider>
  );
};

export default FileReceive;
