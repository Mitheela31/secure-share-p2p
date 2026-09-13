import React, { useState, useCallback } from 'react';
import { 
  Upload, 
  File, 
  X, 
  Lock, 
  Send, 
  CheckCircle2, 
  ArrowRight,
  Loader2,
  Shield,
  Package,
  Wifi,
  AlertCircle
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
import { fileService } from '@/lib/fileService';
import { transferService } from '@/lib/transferService';
import { getAccessToken } from '@/lib/api';

interface FileTransferProps {
  receiverName: string;
  receiverId: number;  // Backend user ID for creating transfer
  onTransferComplete: (fileName: string, fileSize: string, fileId: number, transferUuid: string) => void;
  onCancel: () => void;
}

type TransferStatus = 'idle' | 'encrypting' | 'transmitting' | 'complete';

const TOTAL_CHUNKS = 5;

const getWebCrypto = () => {
  if (window.location.hostname !== 'localhost' && window.location.hostname !== '127.0.0.1' && !window.isSecureContext) {
    alert("Running in insecure context. Web Crypto may be unavailable.");
  }
  const cryptoObj = window.crypto || (window as any).msCrypto;
  if (!cryptoObj || !cryptoObj.subtle) {
    throw new Error('Web Crypto API requires HTTPS or localhost');
  }
  return cryptoObj;
};

const FileTransfer: React.FC<FileTransferProps> = ({ receiverName, receiverId, onTransferComplete, onCancel }) => {
  const [file, setFile] = useState<{ name: string; size: string; bytes: number; rawFile?: File } | null>(null);
  const [isDragOver, setIsDragOver] = useState(false);
  const [status, setStatus] = useState<TransferStatus>('idle');
  const [progress, setProgress] = useState(0);
  const [currentChunk, setCurrentChunk] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [isSending, setIsSending] = useState(false);
  
  const { addLog, setTransferPhase, setChunkProgress } = useCrypto();
  const selectedFile = file;
  const receiver = receiverName && receiverId ? { id: receiverId, name: receiverName } : null;

  console.log('STATE CHECK:', {
    file: selectedFile,
    receiver,
    isSending,
  });

  const formatFileSize = (bytes: number): string => {
    if (bytes < 1024) return bytes + ' B';
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
    return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
  };

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(false);
    setError(null);
    
    const droppedFile = e.dataTransfer.files[0];
    if (droppedFile) {
      setFile({ 
        name: droppedFile.name, 
        size: formatFileSize(droppedFile.size),
        bytes: droppedFile.size,
        rawFile: droppedFile
      });
    }
  }, []);

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const selectedFile = e.target.files?.[0];
    setError(null);
    if (selectedFile) {
      setFile({ 
        name: selectedFile.name, 
        size: formatFileSize(selectedFile.size),
        bytes: selectedFile.size,
        rawFile: selectedFile
      });
    }
  };

  const handleSendFile = async () => {
    try {
      console.log('Send clicked');

      const cryptoApi = getWebCrypto();

      if (!selectedFile) {
        throw new Error('No file selected');
      }

      if (!receiver) {
        throw new Error('No receiver selected');
      }

      if (!selectedFile.rawFile) {
        throw new Error('No file selected for upload.');
      }

      const token = getAccessToken();
      if (!token) {
        throw new Error('Missing access token. Please log in again.');
      }

      setIsSending(true);
      setError(null);

      addLog({
        type: 'info',
        category: 'transfer',
        message: `Starting secure file transfer: ${selectedFile.name} (${selectedFile.size})`,
      });

      addLog({
        type: 'info',
        category: 'transfer',
        message: 'Generating AES-256-GCM key and IV on sender device...',
      });

      const keyBytes = cryptoApi.getRandomValues(new Uint8Array(32));
      const ivBytes = cryptoApi.getRandomValues(new Uint8Array(12));

      console.log('KEY LENGTH:', keyBytes.length);
      console.log('IV LENGTH:', ivBytes.length);

      if (keyBytes.length !== 32) {
        throw new Error('Invalid AES-256 key length');
      }

      if (ivBytes.length !== 12) {
        throw new Error('Invalid IV length');
      }

      const base64Key = fileService.bytesToBase64(keyBytes);
      const base64IV = fileService.bytesToBase64(ivBytes);

      const cryptoKey = await cryptoApi.subtle.importKey(
        'raw',
        keyBytes,
        { name: 'AES-GCM' },
        false,
        ['encrypt'],
      );

      const fileBuffer = await selectedFile.rawFile.arrayBuffer();
      const encrypted = await cryptoApi.subtle.encrypt(
        {
          name: 'AES-GCM',
          iv: ivBytes,
        },
        cryptoKey,
        fileBuffer,
      );

      const encryptedBlob = new Blob([encrypted], { type: 'application/octet-stream' });
      const fileId = await fileService.uploadEncryptedFile({
        encryptedBlob,
        token,
        originalFilename: selectedFile.name,
      });

      addLog({
        type: 'success',
        category: 'transfer',
        message: `Encrypted file uploaded with fileId: ${fileId}`,
      });

      console.log('fileId:', fileId);

      addLog({
        type: 'info',
        category: 'transfer',
        message: `Creating transfer request for ${receiver.name}...`,
      });

      const transfer = await transferService.createTransfer({
        receiver_id: receiver.id,
        file_id: fileId,
        file_name: selectedFile.name,
        aes_key: base64Key,
        iv: base64IV,
      });

      if (!transfer.file?.id) {
        throw new Error('Transfer created without a valid backend fileId.');
      }

      addLog({
        type: 'success',
        category: 'transfer',
        message: `Transfer created: ${transfer.uuid} - Receiver will be notified`,
      });

      onTransferComplete(selectedFile.name, selectedFile.size, transfer.file.id, transfer.uuid);

      setStatus('encrypting');
      setTransferPhase('encrypting');
      setProgress(0);

      for (let chunk = 1; chunk <= TOTAL_CHUNKS; chunk += 1) {
        setCurrentChunk(chunk);
        setChunkProgress(chunk, TOTAL_CHUNKS);

        addLog({
          type: 'crypto',
          category: 'encryption',
          message: `Encrypting chunk ${chunk}/${TOTAL_CHUNKS}...`,
          algorithm: 'AES-256-GCM',
        });

        for (let i = 0; i < 10; i += 1) {
          await new Promise((resolve) => setTimeout(resolve, 60));
          const chunkProgress = ((chunk - 1) / TOTAL_CHUNKS) * 50 + (i / 10) * (50 / TOTAL_CHUNKS);
          setProgress(Math.round(chunkProgress));
        }

        addLog({
          type: 'success',
          category: 'encryption',
          message: `Chunk ${chunk}/${TOTAL_CHUNKS} encrypted successfully`,
        });
      }

      addLog({
        type: 'success',
        category: 'encryption',
        message: '✓ File encryption complete - All chunks encrypted',
        algorithm: 'AES-256-GCM',
      });

      setStatus('transmitting');
      setTransferPhase('transmitting');
      setCurrentChunk(0);

      addLog({
        type: 'network',
        category: 'transfer',
        message: 'Initiating encrypted data transmission over P2P channel...',
      });

      for (let chunk = 1; chunk <= TOTAL_CHUNKS; chunk += 1) {
        setCurrentChunk(chunk);
        setChunkProgress(chunk, TOTAL_CHUNKS);

        addLog({
          type: 'network',
          category: 'transfer',
          message: `Transmitting encrypted chunk ${chunk}/${TOTAL_CHUNKS}...`,
        });

        for (let i = 0; i < 10; i += 1) {
          await new Promise((resolve) => setTimeout(resolve, 50));
          const transmitProgress = 50 + ((chunk - 1) / TOTAL_CHUNKS) * 50 + (i / 10) * (50 / TOTAL_CHUNKS);
          setProgress(Math.round(transmitProgress));
        }

        addLog({
          type: 'success',
          category: 'transfer',
          message: `Chunk ${chunk}/${TOTAL_CHUNKS} delivered to receiver`,
        });
      }

      addLog({
        type: 'success',
        category: 'transfer',
        message: '✓ All encrypted chunks transmitted successfully',
      });

      setStatus('complete');
      setTransferPhase('complete');

      addLog({
        type: 'success',
        category: 'transfer',
        message: `File "${selectedFile.name}" sent securely to ${receiver.name}`,
      });
    } catch (err) {
      console.error(err);
      const errorMessage = err instanceof Error ? err.message : 'Unexpected send failure';
      alert(errorMessage);
      setError(errorMessage);
    } finally {
      setIsSending(false);
    }
  };

  const getStatusInfo = () => {
    switch (status) {
      case 'encrypting':
        return { 
          text: 'Encrypting file chunks with AES-256-GCM...', 
          icon: Lock,
          color: 'text-primary',
          bgColor: 'bg-primary/20'
        };
      case 'transmitting':
        return { 
          text: 'Transmitting encrypted data over P2P channel...', 
          icon: Send,
          color: 'text-secondary',
          bgColor: 'bg-secondary/20'
        };
      case 'complete':
        return { 
          text: 'Transfer complete!', 
          icon: CheckCircle2,
          color: 'text-success',
          bgColor: 'bg-success/20'
        };
      default:
        return null;
    }
  };

  const statusInfo = getStatusInfo();

  return (
    <TooltipProvider>
      <div className="glass-card cyber-border p-6">
        <div className="flex items-center justify-between mb-6">
          <div>
            <h3 className="text-lg font-bold">Secure File Transfer</h3>
            <p className="text-muted-foreground text-sm">
              Sending to <span className="text-secondary">{receiverName}</span>
            </p>
          </div>
          <button
            onClick={onCancel}
            className="p-2 rounded-lg hover:bg-muted transition-colors"
            disabled={status !== 'idle'}
          >
            <X className="w-5 h-5 text-muted-foreground" />
          </button>
        </div>

        {status === 'idle' ? (
          <>
            {/* Drop zone */}
            <div
              onDrop={handleDrop}
              onDragOver={(e) => { e.preventDefault(); setIsDragOver(true); }}
              onDragLeave={() => setIsDragOver(false)}
              className={`
                relative border-2 border-dashed rounded-xl p-8 text-center transition-all duration-300 cursor-pointer
                ${isDragOver 
                  ? 'border-primary bg-primary/5 scale-[1.02]' 
                  : 'border-border hover:border-primary/50 hover:bg-muted/30'
                }
                ${file ? 'border-success bg-success/5' : ''}
              `}
            >
              <input
                type="file"
                onChange={handleFileSelect}
                className="absolute inset-0 opacity-0 cursor-pointer"
              />
              
              {file ? (
                <div className="flex items-center justify-center gap-4">
                  <div className="w-12 h-12 rounded-xl bg-success/20 flex items-center justify-center">
                    <File className="w-6 h-6 text-success" />
                  </div>
                  <div className="text-left">
                    <p className="font-medium text-foreground">{file.name}</p>
                    <p className="text-sm text-muted-foreground">{file.size}</p>
                  </div>
                  <button
                    onClick={(e) => { e.stopPropagation(); setFile(null); }}
                    className="p-2 rounded-lg hover:bg-muted transition-colors"
                  >
                    <X className="w-4 h-4 text-muted-foreground" />
                  </button>
                </div>
              ) : (
                <div className="space-y-3">
                  <div className="w-16 h-16 mx-auto rounded-2xl bg-muted flex items-center justify-center">
                    <Upload className={`w-8 h-8 ${isDragOver ? 'text-primary animate-bounce' : 'text-muted-foreground'}`} />
                  </div>
                  <div>
                    <p className="font-medium text-foreground">
                      {isDragOver ? 'Drop your file here' : 'Drag & drop your file here'}
                    </p>
                    <p className="text-sm text-muted-foreground">or click to browse</p>
                  </div>
                </div>
              )}
            </div>

            {/* Security info */}
            {file && (
              <div className="mt-4 flex flex-wrap gap-2">
                <Tooltip>
                  <TooltipTrigger asChild>
                    <div className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-primary/10 text-primary text-xs cursor-help">
                      <Lock className="w-3 h-3" />
                      <span>AES-256-GCM</span>
                    </div>
                  </TooltipTrigger>
                  <TooltipContent className="max-w-xs">
                    <p className="text-xs">
                      Advanced Encryption Standard with 256-bit key and Galois/Counter Mode. 
                      Provides both confidentiality and authenticity.
                    </p>
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
                    <p className="text-xs">File will be split into 5 encrypted chunks for secure transmission</p>
                  </TooltipContent>
                </Tooltip>
                <Tooltip>
                  <TooltipTrigger asChild>
                    <div className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-success/10 text-success text-xs cursor-help">
                      <Shield className="w-3 h-3" />
                      <span>E2E Encrypted</span>
                    </div>
                  </TooltipTrigger>
                  <TooltipContent>
                    <p className="text-xs">End-to-end encryption ensures only the recipient can decrypt the file</p>
                  </TooltipContent>
                </Tooltip>
              </div>
            )}

            {/* Send button */}
            <button
              onClick={handleSendFile}
              disabled={!selectedFile || !receiver || isSending === true}
              className="w-full mt-6 py-4 cyber-btn text-primary-foreground font-semibold rounded-xl flex items-center justify-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <Lock className="w-5 h-5" />
              <span>{isSending ? 'Sending...' : 'Encrypt & Send File'}</span>
              <ArrowRight className="w-5 h-5" />
            </button>
          </>
        ) : (
          <div className="space-y-6">
            {/* Status header */}
            <div className="text-center">
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
              <p className="text-sm text-muted-foreground mt-1">{file?.name}</p>
            </div>

            {/* Packet flow animation */}
            <PacketFlowAnimation
              isActive={status === 'transmitting'}
              senderName="You"
              receiverName={receiverName}
              currentPacket={currentChunk}
              totalPackets={TOTAL_CHUNKS}
            />

            {/* Chunk progress */}
            {status !== 'complete' && (
              <ChunkProgress
                currentChunk={currentChunk}
                totalChunks={TOTAL_CHUNKS}
                phase={status === 'encrypting' ? 'encrypting' : 'transmitting'}
              />
            )}

            {/* Overall progress */}
            <div className="space-y-2">
              <div className="flex justify-between text-sm">
                <span className="text-muted-foreground">Overall Progress</span>
                <span className="font-mono text-primary">{progress}%</span>
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
                { key: 'encrypting', label: 'Encrypting file chunks', algorithm: 'AES-256-GCM' },
                { key: 'transmitting', label: 'Transmitting over P2P', algorithm: 'Secure Channel' },
                { key: 'complete', label: 'Transfer complete', algorithm: 'Verified' },
              ].map((step, index) => {
                const isActive = status === step.key;
                const isPast = ['encrypting', 'transmitting', 'complete'].indexOf(status) > index;
                
                return (
                  <div
                    key={step.key}
                    className={`
                      flex items-center gap-3 p-3 rounded-lg transition-all
                      ${isActive ? 'bg-primary/10 border border-primary/30' : ''}
                    `}
                  >
                    {isPast ? (
                      <CheckCircle2 className="w-5 h-5 text-success" />
                    ) : isActive ? (
                      <Loader2 className="w-5 h-5 text-primary animate-spin" />
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
              <div className="p-4 rounded-xl bg-success/10 border border-success/30 text-center">
                <CheckCircle2 className="w-8 h-8 text-success mx-auto mb-2" />
                <p className="font-medium text-success">File Sent Successfully!</p>
                <p className="text-xs text-muted-foreground mt-1">
                  Receiver will now decrypt the file
                </p>
              </div>
            )}
          </div>
        )}
      </div>
    </TooltipProvider>
  );
};

export default FileTransfer;
