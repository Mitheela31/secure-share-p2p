import React from 'react';
import { Lock, Send, Download, Clock, CheckCircle2, Shield, Key } from 'lucide-react';
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";

export interface TransferRecord {
  id: string;
  transferUuid?: string;
  fileName: string;
  fileSize: string;
  fileId?: number;
  fileUuid?: string;
  aesKey?: string;
  iv?: string;
  mimeType?: string;
  sender: string;
  receiver: string;
  timestamp: Date;
  type: 'sent' | 'received';
  algorithms?: {
    encryption: string;
    keyExchange: string;
    hash: string;
  };
}

interface TransferHistoryProps {
  transfers: TransferRecord[];
  currentUser: string;
  onDownload?: (transfer: TransferRecord) => void;
  downloadingTransferId?: string | null;
  downloadStatus?: Record<string, 'idle' | 'downloading' | 'completed' | 'failed'>;
  downloadFailureReasons?: Record<string, string>;
}

const TransferHistory: React.FC<TransferHistoryProps> = ({
  transfers,
  currentUser,
  onDownload,
  downloadingTransferId,
  downloadStatus = {},
  downloadFailureReasons = {},
}) => {
  const defaultAlgorithms = {
    encryption: 'AES-256-GCM',
    keyExchange: 'ECDH P-256',
    hash: 'SHA-256',
  };

  // Helper to get download button state
  const getDownloadButtonState = (transferId: string) => {
    const status = downloadStatus[transferId];
    return {
      isLoading: status === 'downloading',
      isCompleted: status === 'completed',
      isFailed: status === 'failed',
      isDisabled: status === 'downloading' || status === 'completed',
    };
  };

  // Helper to get download button text
  const getDownloadButtonText = (transferId: string) => {
    const status = downloadStatus[transferId];
    switch (status) {
      case 'downloading':
        return 'Decrypting...';
      case 'completed':
        return '✓ Decrypted';
      case 'failed':
        return `❌ Failed (${downloadFailureReasons[transferId] || 'error'})`;
      default:
        return 'Download & Decrypt';
    }
  };

  if (transfers.length === 0) {
    return (
      <div className="glass-card cyber-border p-6">
        <div className="text-center py-8">
          <div className="w-16 h-16 mx-auto rounded-2xl bg-muted flex items-center justify-center mb-4">
            <Clock className="w-8 h-8 text-muted-foreground" />
          </div>
          <p className="text-muted-foreground">No transfer history yet</p>
          <p className="text-sm text-muted-foreground mt-1">
            Your secure file transfers will appear here
          </p>
        </div>
      </div>
    );
  }

  return (
    <TooltipProvider>
      <div className="glass-card cyber-border overflow-hidden">
        <div className="p-4 border-b border-border flex items-center justify-between">
          <h3 className="font-bold flex items-center gap-2">
            <Clock className="w-5 h-5 text-primary" />
            Transfer History
          </h3>
          <div className="flex items-center gap-2 text-xs text-muted-foreground">
            <Lock className="w-3 h-3 text-success" />
            <span>All transfers encrypted</span>
          </div>
        </div>

        {/* Table header for desktop */}
        <div className="hidden md:grid grid-cols-12 gap-4 px-4 py-3 bg-muted/50 text-xs font-medium text-muted-foreground">
          <div className="col-span-3">File</div>
          <div className="col-span-2">Sender / Receiver</div>
          <div className="col-span-3">Algorithms</div>
          <div className="col-span-2">Time</div>
          <div className="col-span-2">Status</div>
        </div>
        
        <div className="divide-y divide-border">
          {transfers.map((transfer) => {
            const algorithms = transfer.algorithms || defaultAlgorithms;
            
            return (
              <div key={transfer.id} className="p-4 hover:bg-muted/30 transition-colors">
                {/* Mobile layout */}
                <div className="md:hidden space-y-3">
                  <div className="flex items-start gap-3">
                    <div className={`
                      w-10 h-10 rounded-lg flex items-center justify-center shrink-0
                      ${transfer.type === 'sent' ? 'bg-primary/20' : 'bg-secondary/20'}
                    `}>
                      {transfer.type === 'sent' ? (
                        <Send className="w-5 h-5 text-primary" />
                      ) : (
                        <Download className="w-5 h-5 text-secondary" />
                      )}
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2">
                        <p className="font-medium truncate">{transfer.fileName}</p>
                        <Tooltip>
                          <TooltipTrigger>
                            <Lock className="w-3 h-3 text-success shrink-0" />
                          </TooltipTrigger>
                          <TooltipContent>
                            <p className="text-xs">End-to-end encrypted transfer</p>
                          </TooltipContent>
                        </Tooltip>
                      </div>
                      <p className="text-sm text-muted-foreground">
                        {transfer.type === 'sent' 
                          ? `To: ${transfer.receiver}` 
                          : `From: ${transfer.sender}`
                        }
                      </p>
                    </div>
                    <div className="flex items-center gap-1.5 px-2 py-1 rounded-full bg-success/10 text-success text-xs font-medium shrink-0">
                      <CheckCircle2 className="w-3 h-3" />
                      <span>{transfer.type === 'sent' ? 'Sent' : 'Received'}</span>
                    </div>
                  </div>
                  
                  <div className="flex flex-wrap gap-1.5 pl-13">
                    <span className="px-2 py-0.5 rounded bg-primary/10 text-primary text-[10px] font-mono">
                      {algorithms.encryption}
                    </span>
                    <span className="px-2 py-0.5 rounded bg-secondary/10 text-secondary text-[10px] font-mono">
                      {algorithms.keyExchange}
                    </span>
                  </div>

                  <div className="flex items-center gap-3 text-xs text-muted-foreground pl-13">
                    <span>{transfer.fileSize}</span>
                    <span>•</span>
                    <span>{transfer.timestamp.toLocaleString()}</span>
                  </div>

                  {transfer.type === 'received' && (transfer.fileId || transfer.transferUuid) && onDownload && (
                    <div className="pl-13">
                      {(() => {
                        const btnState = getDownloadButtonState(transfer.id);
                        let buttonClasses = "inline-flex items-center gap-2 rounded-lg border px-3 py-2 text-xs font-medium transition-colors";
                        
                        if (btnState.isCompleted) {
                          buttonClasses += " border-success/40 text-success hover:bg-success/10";
                        } else if (btnState.isFailed) {
                          buttonClasses += " border-destructive/40 text-destructive hover:bg-destructive/10";
                        } else if (btnState.isDisabled) {
                          buttonClasses += " border-secondary/40 text-secondary/50 cursor-not-allowed";
                        } else {
                          buttonClasses += " border-secondary/40 text-secondary hover:bg-secondary/10";
                        }

                        return (
                          <button
                            onClick={() => !btnState.isDisabled && onDownload(transfer)}
                            disabled={btnState.isDisabled}
                            className={buttonClasses}
                          >
                            <Download className="w-3.5 h-3.5" />
                            <span>{getDownloadButtonText(transfer.id)}</span>
                          </button>
                        );
                      })()}
                    </div>
                  )}
                </div>

                {/* Desktop layout */}
                <div className="hidden md:grid grid-cols-12 gap-4 items-center">
                  {/* File */}
                  <div className="col-span-3 flex items-center gap-3">
                    <div className={`
                      w-10 h-10 rounded-lg flex items-center justify-center shrink-0
                      ${transfer.type === 'sent' ? 'bg-primary/20' : 'bg-secondary/20'}
                    `}>
                      {transfer.type === 'sent' ? (
                        <Send className="w-5 h-5 text-primary" />
                      ) : (
                        <Download className="w-5 h-5 text-secondary" />
                      )}
                    </div>
                    <div className="min-w-0">
                      <div className="flex items-center gap-2">
                        <p className="font-medium truncate">{transfer.fileName}</p>
                        <Tooltip>
                          <TooltipTrigger>
                            <Lock className="w-3 h-3 text-success shrink-0" />
                          </TooltipTrigger>
                          <TooltipContent>
                            <p className="text-xs">End-to-end encrypted</p>
                          </TooltipContent>
                        </Tooltip>
                      </div>
                      <p className="text-xs text-muted-foreground">{transfer.fileSize}</p>
                    </div>
                  </div>

                  {/* Sender/Receiver */}
                  <div className="col-span-2 text-sm">
                    {transfer.type === 'sent' 
                      ? <span>To: <span className="text-secondary">{transfer.receiver}</span></span>
                      : <span>From: <span className="text-primary">{transfer.sender}</span></span>
                    }
                  </div>

                  {/* Algorithms */}
                  <div className="col-span-3 flex flex-wrap gap-1">
                    <Tooltip>
                      <TooltipTrigger>
                        <span className="px-1.5 py-0.5 rounded bg-primary/10 text-primary text-[10px] font-mono cursor-help">
                          {algorithms.encryption}
                        </span>
                      </TooltipTrigger>
                      <TooltipContent>
                        <p className="text-xs">Symmetric encryption algorithm</p>
                      </TooltipContent>
                    </Tooltip>
                    <Tooltip>
                      <TooltipTrigger>
                        <span className="px-1.5 py-0.5 rounded bg-secondary/10 text-secondary text-[10px] font-mono cursor-help">
                          {algorithms.keyExchange}
                        </span>
                      </TooltipTrigger>
                      <TooltipContent>
                        <p className="text-xs">Key exchange protocol</p>
                      </TooltipContent>
                    </Tooltip>
                    <Tooltip>
                      <TooltipTrigger>
                        <span className="px-1.5 py-0.5 rounded bg-success/10 text-success text-[10px] font-mono cursor-help">
                          {algorithms.hash}
                        </span>
                      </TooltipTrigger>
                      <TooltipContent>
                        <p className="text-xs">Hashing algorithm</p>
                      </TooltipContent>
                    </Tooltip>
                  </div>

                  {/* Time */}
                  <div className="col-span-2 text-sm text-muted-foreground">
                    {transfer.timestamp.toLocaleTimeString()}
                  </div>

                  {/* Status */}
                  <div className="col-span-2">
                    <div className="flex items-center gap-2 flex-wrap">
                      <div className="flex items-center gap-1.5 px-2 py-1 rounded-full bg-success/10 text-success text-xs font-medium w-fit">
                        <CheckCircle2 className="w-3 h-3" />
                        <span>{transfer.type === 'sent' ? 'Sent' : 'Received'}</span>
                      </div>
                      {transfer.type === 'received' && (transfer.fileId || transfer.transferUuid) && onDownload && (
                        (() => {
                          const btnState = getDownloadButtonState(transfer.id);
                          let buttonClasses = "inline-flex items-center gap-1.5 rounded-lg border px-2 py-1 text-xs font-medium transition-colors";
                          
                          if (btnState.isCompleted) {
                            buttonClasses += " border-success/40 text-success hover:bg-success/10";
                          } else if (btnState.isFailed) {
                            buttonClasses += " border-destructive/40 text-destructive hover:bg-destructive/10";
                          } else if (btnState.isDisabled) {
                            buttonClasses += " border-secondary/40 text-secondary/50 cursor-not-allowed";
                          } else {
                            buttonClasses += " border-secondary/40 text-secondary hover:bg-secondary/10";
                          }

                          return (
                            <button
                              onClick={() => !btnState.isDisabled && onDownload(transfer)}
                              disabled={btnState.isDisabled}
                              className={buttonClasses}
                            >
                              <Download className="w-3 h-3" />
                              <span>{getDownloadButtonText(transfer.id)}</span>
                            </button>
                          );
                        })()
                      )}
                    </div>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </TooltipProvider>
  );
};

export default TransferHistory;
