import React, { useState, useEffect, useCallback } from 'react';
import { 
  Download, 
  ArrowLeft, 
  Shield, 
  User, 
  CheckCircle2,
  X,
  Bell,
  History,
  Send,
  Terminal,
  Key,
  RefreshCw
} from 'lucide-react';
import { useCrypto } from '@/contexts/CryptoContext';
import FileReceive from './FileReceive';
import TransferHistory, { TransferRecord } from './TransferHistory';
import GlobalBanner from './GlobalBanner';
import SecurityLog from './SecurityLog';
import KeyExchangeVisualizer from './KeyExchangeVisualizer';
import { transferService, TransferListItem } from '@/lib/transferService';
import fileService from '@/lib/fileService';

interface ReceiverDashboardProps {
  username: string;
  onBack: () => void;
  onLogout: () => void;
  transfers: TransferRecord[];
  onNewTransfer: (transfer: TransferRecord) => void;
}

interface IncomingRequest {
  id: string;
  transferId: number;  // Backend transfer ID for API calls
  sender: string;
  fileName: string;
  fileSize: string;
}

type ConnectionState = 'waiting' | 'request' | 'key-exchange' | 'connected' | 'receiving' | 'complete';

// Polling interval for checking pending transfers (in milliseconds)
const POLL_INTERVAL = 5000;

const ReceiverDashboard: React.FC<ReceiverDashboardProps> = ({ 
  username, 
  onBack, 
  onLogout,
  transfers,
  onNewTransfer
}) => {
  const [connectionState, setConnectionState] = useState<ConnectionState>('waiting');
  const [incomingRequest, setIncomingRequest] = useState<IncomingRequest | null>(null);
  const [showHistory, setShowHistory] = useState(false);
  const [showSecurityLog, setShowSecurityLog] = useState(true);
  const [isPolling, setIsPolling] = useState(true);
  const [lastChecked, setLastChecked] = useState<Date | null>(null);
  const [downloadingTransferId, setDownloadingTransferId] = useState<string | null>(null);
  
  // Track download status per transfer: idle | downloading | completed | failed
  const [downloadStatus, setDownloadStatus] = useState<Record<string, 'idle' | 'downloading' | 'completed' | 'failed'>>({});
  const [downloadFailureReasons, setDownloadFailureReasons] = useState<Record<string, string>>({});

  const { addLog, resetCryptoState, setConnectionEstablished, setSecureChannelActive } = useCrypto();

  /**
   * Fetch pending transfer requests from the backend.
   * This replaces the hardcoded demo data that previously showed "Alice_Secure".
   * 
   * Only shows incoming requests when a real user has initiated a transfer
   * to this receiver through the backend API.
   */
  const checkPendingTransfers = useCallback(async () => {
    // Don't poll if already handling a request
    if (connectionState !== 'waiting') {
      return;
    }

    try {
      const pendingTransfers = await transferService.getPendingTransfers();
      setLastChecked(new Date());

      // Check if there are any pending transfers that haven't been shown yet
      if (pendingTransfers.length > 0) {
        const firstPending = pendingTransfers[0];
        
        // Only set incoming request if we don't already have one
        if (!incomingRequest) {
          addLog({
            type: 'network',
            category: 'connection',
            message: `Incoming connection request from ${firstPending.sender_username}`,
          });

          setIncomingRequest({
            id: firstPending.uuid,
            transferId: firstPending.id,
            sender: firstPending.sender_username,
            fileName: firstPending.file_name,
            fileSize: firstPending.file_size_formatted,
          });
          setConnectionState('request');

          addLog({
            type: 'info',
            category: 'connection',
            message: `Connection request from ${firstPending.sender_username} - awaiting your response`,
          });
        }
      }
    } catch (error) {
      // Silently handle errors during polling - user might not be logged in yet
      // or network might be temporarily unavailable
      console.debug('Failed to check pending transfers:', error);
    }
  }, [connectionState, incomingRequest, addLog]);

  /**
   * Poll for pending transfers periodically.
   * This allows the receiver to see incoming requests in near real-time
   * without requiring WebSocket (can be upgraded to WebSocket later).
   */
  useEffect(() => {
    // Initial check on component mount
    checkPendingTransfers();

    // Set up polling interval only if in waiting state
    if (isPolling && connectionState === 'waiting') {
      const pollTimer = setInterval(checkPendingTransfers, POLL_INTERVAL);
      
      return () => clearInterval(pollTimer);
    }
  }, [isPolling, connectionState, checkPendingTransfers]);

  /**
   * Accept incoming transfer request.
   * Calls backend API to update transfer status, then proceeds with key exchange.
   */
  const handleAccept = async () => {
    if (!incomingRequest) return;

    try {
      // Call backend to accept the transfer
      await transferService.performAction(incomingRequest.transferId, 'accept');
      
      addLog({
        type: 'success',
        category: 'connection',
        message: 'Connection request accepted',
      });

      addLog({
        type: 'info',
        category: 'connection',
        message: 'Initiating secure key exchange protocol...',
      });

      setConnectionState('key-exchange');
    } catch (error) {
      addLog({
        type: 'error',
        category: 'connection',
        message: 'Failed to accept transfer request',
      });
      console.error('Failed to accept transfer:', error);
    }
  };

  const handleKeyExchangeComplete = () => {
    setConnectionEstablished(true);
    setSecureChannelActive(true);

    addLog({
      type: 'success',
      category: 'connection',
      message: 'Peer authenticated – Secure channel established',
    });

    setConnectionState('connected');
    // Simulate file transfer starting
    setTimeout(() => setConnectionState('receiving'), 1000);
  };

  /**
   * Reject incoming transfer request.
   * Calls backend API to update transfer status and resets to waiting state.
   */
  const handleReject = async () => {
    if (!incomingRequest) return;

    try {
      // Call backend to reject the transfer
      await transferService.performAction(incomingRequest.transferId, 'reject');
      
      addLog({
        type: 'warning',
        category: 'connection',
        message: 'Connection request rejected',
      });
    } catch (error) {
      addLog({
        type: 'error',
        category: 'connection',
        message: 'Failed to reject transfer request',
      });
      console.error('Failed to reject transfer:', error);
    }

    setIncomingRequest(null);
    setConnectionState('waiting');
  };

  const handleReceiveComplete = async () => {
    if (incomingRequest) {
      let fileId: number | undefined;
      let fileUuid: string | undefined;
      let transferUuid: string | undefined;

      try {
        // Pull the authoritative backend transfer record so the history entry
        // carries the real file identifier required by the download endpoint.
        const transfer = await transferService.getTransferById(incomingRequest.transferId);
        fileId = transfer.file.id;
        fileUuid = transfer.file.uuid;
        transferUuid = transfer.uuid;
        const aesKey = transfer.aes_key ?? transfer.encrypted_aes_key ?? undefined;
        const iv = transfer.iv ?? transfer.file_iv ?? undefined;
        const mimeType = transfer.file.mime_type;

        const newTransfer: TransferRecord = {
          id: incomingRequest.transferId.toString(),
          transferUuid,
          fileName: incomingRequest.fileName,
          fileSize: incomingRequest.fileSize,
          fileId,
          fileUuid,
          aesKey,
          iv,
          mimeType,
          sender: incomingRequest.sender,
          receiver: username,
          timestamp: new Date(),
          type: 'received',
          algorithms: {
            encryption: 'AES-256-GCM',
            keyExchange: 'ECDH P-256',
            hash: 'SHA-256',
          },
        };

        onNewTransfer(newTransfer);
        setConnectionState('complete');

        addLog({
          type: 'success',
          category: 'transfer',
          message: 'File stored securely on your device',
        });
        return;
      } catch (error) {
        console.debug('Unable to fetch transfer details for download metadata:', error);
      }

      const newTransfer: TransferRecord = {
        id: incomingRequest.transferId.toString(),
        transferUuid,
        fileName: incomingRequest.fileName,
        fileSize: incomingRequest.fileSize,
        fileId,
        fileUuid,
        aesKey: undefined,
        iv: undefined,
        mimeType: undefined,
        sender: incomingRequest.sender,
        receiver: username,
        timestamp: new Date(),
        type: 'received',
        algorithms: {
          encryption: 'AES-256-GCM',
          keyExchange: 'ECDH P-256',
          hash: 'SHA-256',
        },
      };
      onNewTransfer(newTransfer);
    }
    setConnectionState('complete');

    addLog({
      type: 'success',
      category: 'transfer',
      message: 'File stored securely on your device',
    });
  };

  const handleDownloadTransfer = async (transfer: TransferRecord) => {
    let transferIdForLookup: number | undefined;
    if (transfer.id) {
      const parsedTransferId = Number.parseInt(transfer.id, 10);
      if (Number.isFinite(parsedTransferId) && parsedTransferId > 0) {
        transferIdForLookup = parsedTransferId;
      }
    }

    setDownloadingTransferId(transfer.id);
    setDownloadStatus(prev => ({ ...prev, [transfer.id]: 'downloading' }));

    try {
      const resolvedFileId = transfer.fileId ?? undefined;
      let originalFilename = transfer.fileName;
      let iv = transfer.iv?.trim() ? transfer.iv : undefined;
      let aesKey = transfer.aesKey?.trim() ? transfer.aesKey : undefined;
      const mimeType = transfer.mimeType ?? 'application/pdf';

      let fileId = resolvedFileId;

      if (!fileId || !iv || !aesKey) {
        const downloadContext = await transferService.resolveDownloadContext({
          transferId: transferIdForLookup,
          transferUuid: transfer.transferUuid,
        });

        fileId = downloadContext.fileId;
        originalFilename = downloadContext.fileName;
        iv = downloadContext.iv;
        aesKey = downloadContext.aesKey;
      }

      if (!fileId) {
        throw new Error('Invalid fileId');
      }

      if (!originalFilename) {
        throw new Error('Original filename missing');
      }

      if (!iv) {
        throw new Error('IV missing');
      }

      if (!aesKey) {
        throw new Error('key missing');
      }

      addLog({
        type: 'info',
        category: 'transfer',
        message: `Downloading and decrypting ${originalFilename}...`,
      });

      await fileService.downloadAndDecryptFile({
        fileId,
        fileName: originalFilename,
        base64Key: aesKey,
        base64IV: iv,
        mimeType,
      });

      // Mark as completed
      setDownloadStatus(prev => ({ ...prev, [transfer.id]: 'completed' }));
      setDownloadFailureReasons(prev => {
        const next = { ...prev };
        delete next[transfer.id];
        return next;
      });

      addLog({
        type: 'success',
        category: 'transfer',
        message: `✓ ${originalFilename} decrypted and downloaded successfully`,
      });

    } catch (error) {
      // Mark as failed
      setDownloadStatus(prev => ({ ...prev, [transfer.id]: 'failed' }));

      const errorMessage = error instanceof Error ? error.message : 'Unknown error';
      setDownloadFailureReasons(prev => ({ ...prev, [transfer.id]: errorMessage }));
      addLog({
        type: 'error',
        category: 'transfer',
        message: `Download failed for ${transfer.fileName}: ${errorMessage}`,
      });
      console.error('Download failed:', error);

      // Auto-clear failed state back to idle after 5 seconds.
      setTimeout(() => {
        setDownloadStatus(prev => {
          const newStatus = { ...prev };
          delete newStatus[transfer.id];
          return newStatus;
        });
        setDownloadFailureReasons(prev => {
          const next = { ...prev };
          delete next[transfer.id];
          return next;
        });
      }, 5000);
    } finally {
      setDownloadingTransferId(null);
    }
  };

  const resetConnection = () => {
    setIncomingRequest(null);
    setConnectionState('waiting');
    resetCryptoState();
  };

  return (
    <div className="min-h-screen p-4 md:p-8 relative overflow-hidden">
      {/* Background effects */}
      <div className="absolute inset-0 bg-cyber-grid bg-grid opacity-20" />
      <div className="absolute bottom-0 left-0 w-[600px] h-[600px] bg-secondary/5 rounded-full blur-3xl" />
      
      <div className="max-w-7xl mx-auto relative z-10">
        {/* Header */}
        <header className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-6">
          <div className="flex items-center gap-4">
            <button
              onClick={onBack}
              className="p-2 rounded-lg hover:bg-muted transition-colors"
            >
              <ArrowLeft className="w-5 h-5" />
            </button>
            <div>
              <div className="flex items-center gap-2">
                <Download className="w-5 h-5 text-secondary" />
                <h1 className="text-2xl font-bold">Receiver Dashboard</h1>
              </div>
              <div className="flex items-center gap-2 text-sm text-muted-foreground">
                <User className="w-4 h-4" />
                <span>{username}</span>
                <span className="w-2 h-2 rounded-full bg-success" />
                <span className="text-success">Ready to receive</span>
              </div>
            </div>
          </div>
          
          <div className="flex items-center gap-3">
            <button
              onClick={() => setShowSecurityLog(!showSecurityLog)}
              className={`flex items-center gap-2 px-4 py-2 rounded-lg border transition-all ${
                showSecurityLog 
                  ? 'border-success bg-success/10 text-success' 
                  : 'border-border hover:border-success/50'
              }`}
            >
              <Terminal className="w-4 h-4" />
              <span className="hidden sm:inline">Console</span>
            </button>
            <button
              onClick={() => setShowHistory(!showHistory)}
              className={`flex items-center gap-2 px-4 py-2 rounded-lg border transition-all ${
                showHistory 
                  ? 'border-secondary bg-secondary/10 text-secondary' 
                  : 'border-border hover:border-secondary/50'
              }`}
            >
              <History className="w-4 h-4" />
              <span className="hidden sm:inline">History</span>
              {transfers.length > 0 && (
                <span className="px-1.5 py-0.5 rounded-full bg-secondary text-secondary-foreground text-xs">
                  {transfers.filter(t => t.type === 'received').length}
                </span>
              )}
            </button>
            <button
              onClick={onLogout}
              className="px-4 py-2 rounded-lg border border-border hover:border-destructive hover:text-destructive transition-all"
            >
              Sign Out
            </button>
          </div>
        </header>

        {/* Global Banner */}
        <GlobalBanner username={username} />

        {showHistory ? (
          <div className="animate-fade-in-up">
            <TransferHistory
              transfers={transfers.filter(t => t.type === 'received')}
              currentUser={username}
              onDownload={handleDownloadTransfer}
              downloadingTransferId={downloadingTransferId}
              downloadStatus={downloadStatus}
              downloadFailureReasons={downloadFailureReasons}
            />
          </div>
        ) : (
          <div className="grid lg:grid-cols-3 gap-6">
            {/* Main content area */}
            <div className="lg:col-span-2 space-y-6">
              {/* Status panel */}
              <div className="glass-card cyber-border p-6">
                <h2 className="font-bold text-lg mb-4 flex items-center gap-2">
                  <Shield className="w-5 h-5 text-success" />
                  Connection Status
                </h2>

                <div className="grid sm:grid-cols-3 gap-4">
                  <div className="flex items-center justify-between p-4 rounded-lg bg-muted/30">
                    <span className="text-muted-foreground">Encryption</span>
                    <span className="flex items-center gap-2 text-success font-medium text-sm">
                      <CheckCircle2 className="w-4 h-4" />
                      AES-256
                    </span>
                  </div>
                  <div className="flex items-center justify-between p-4 rounded-lg bg-muted/30">
                    <span className="text-muted-foreground">P2P Status</span>
                    <span className="flex items-center gap-2 text-success font-medium text-sm">
                      <CheckCircle2 className="w-4 h-4" />
                      Listening
                    </span>
                  </div>
                  <div className="flex items-center justify-between p-4 rounded-lg bg-muted/30">
                    <span className="text-muted-foreground">Secure Channel</span>
                    <span className={`flex items-center gap-2 font-medium text-sm ${
                      connectionState !== 'waiting' && connectionState !== 'request' 
                        ? 'text-success' 
                        : 'text-muted-foreground'
                    }`}>
                      {connectionState !== 'waiting' && connectionState !== 'request' ? (
                        <>
                          <CheckCircle2 className="w-4 h-4" />
                          Established
                        </>
                      ) : (
                        'Waiting...'
                      )}
                    </span>
                  </div>
                </div>
              </div>

              {/* Security Log */}
              {showSecurityLog && (
                <div className="animate-fade-in-up">
                  <SecurityLog maxHeight="300px" />
                </div>
              )}
            </div>

            {/* Incoming requests / Key Exchange / File receive */}
            <div className="lg:col-span-1 space-y-6">
              {connectionState === 'waiting' && (
                <div className="glass-card cyber-border p-6 text-center scan-line">
                  <div className="w-16 h-16 mx-auto rounded-2xl bg-secondary/20 flex items-center justify-center mb-4">
                    <Bell className="w-8 h-8 text-secondary animate-pulse" />
                  </div>
                  <h3 className="font-bold mb-2">Waiting for Connections</h3>
                  <p className="text-muted-foreground text-sm">
                    Your secure channel is active and waiting for incoming file transfers
                  </p>
                  <div className="mt-6 flex flex-col items-center gap-3">
                    <div className="flex items-center gap-2">
                      <div className="w-2 h-2 rounded-full bg-secondary animate-pulse" />
                      <span className="text-xs text-muted-foreground">Listening for senders...</span>
                    </div>
                    {lastChecked && (
                      <span className="text-xs text-muted-foreground">
                        Last checked: {lastChecked.toLocaleTimeString()}
                      </span>
                    )}
                    <button
                      onClick={() => checkPendingTransfers()}
                      className="mt-2 px-4 py-2 text-xs rounded-lg border border-border hover:border-secondary/50 flex items-center gap-2 transition-all"
                    >
                      <RefreshCw className="w-3 h-3" />
                      Check Now
                    </button>
                  </div>
                </div>
              )}

              {connectionState === 'request' && incomingRequest && (
                <div className="glass-card cyber-border animated-border p-6">
                  <div className="flex items-center gap-2 mb-4">
                    <div className="w-3 h-3 rounded-full bg-warning pulse-dot" />
                    <span className="text-warning font-medium">Incoming Connection Request</span>
                  </div>

                  <div className="flex items-center gap-4 mb-6 p-4 rounded-lg bg-muted/30">
                    <div className="w-12 h-12 rounded-full bg-gradient-cyber flex items-center justify-center text-primary-foreground font-bold text-lg">
                      {incomingRequest.sender[0]}
                    </div>
                    <div>
                      <p className="font-bold">{incomingRequest.sender}</p>
                      <p className="text-sm text-muted-foreground flex items-center gap-1">
                        <Send className="w-3 h-3" />
                        wants to share a file
                      </p>
                    </div>
                  </div>

                  <div className="p-3 rounded-lg bg-muted/30 mb-4 text-sm">
                    <p className="text-muted-foreground">File: <span className="text-foreground">{incomingRequest.fileName}</span></p>
                    <p className="text-muted-foreground">Size: <span className="text-foreground">{incomingRequest.fileSize}</span></p>
                  </div>

                  <div className="flex gap-3">
                    <button
                      onClick={handleAccept}
                      className="flex-1 py-3 cyber-btn text-primary-foreground font-semibold rounded-lg flex items-center justify-center gap-2"
                    >
                      <CheckCircle2 className="w-5 h-5" />
                      Accept
                    </button>
                    <button
                      onClick={handleReject}
                      className="flex-1 py-3 rounded-lg border border-destructive text-destructive hover:bg-destructive hover:text-destructive-foreground font-semibold transition-all flex items-center justify-center gap-2"
                    >
                      <X className="w-5 h-5" />
                      Reject
                    </button>
                  </div>
                </div>
              )}

              {connectionState === 'key-exchange' && incomingRequest && (
                <KeyExchangeVisualizer
                  senderName={incomingRequest.sender}
                  receiverName={username}
                  onComplete={handleKeyExchangeComplete}
                />
              )}

              {connectionState === 'connected' && (
                <div className="glass-card cyber-border p-6 text-center">
                  <div className="w-16 h-16 mx-auto rounded-2xl bg-success/20 flex items-center justify-center mb-4">
                    <CheckCircle2 className="w-8 h-8 text-success" />
                  </div>
                  <h3 className="font-bold text-success mb-2">Connection Established!</h3>
                  <p className="text-muted-foreground text-sm">
                    Secure channel active with {incomingRequest?.sender}
                  </p>
                  <p className="text-xs text-success mt-2">
                    Peer authenticated – Waiting for file...
                  </p>
                </div>
              )}

              {connectionState === 'receiving' && incomingRequest && (
                <FileReceive
                  senderName={incomingRequest.sender}
                  fileName={incomingRequest.fileName}
                  fileSize={incomingRequest.fileSize}
                  onReceiveComplete={handleReceiveComplete}
                />
              )}

              {connectionState === 'complete' && (
                <div className="glass-card cyber-border p-6 text-center">
                  <div className="w-16 h-16 mx-auto rounded-2xl bg-success/20 flex items-center justify-center mb-4">
                    <CheckCircle2 className="w-8 h-8 text-success" />
                  </div>
                  <h3 className="font-bold text-success mb-2">Transfer Complete!</h3>
                  <p className="text-muted-foreground text-sm mb-2">
                    File stored securely on your device
                  </p>
                  <p className="text-xs text-success mb-4">
                    ✓ Integrity verified – File decrypted successfully
                  </p>
                  <button
                    onClick={resetConnection}
                    className="px-6 py-2 cyber-btn-secondary text-secondary-foreground rounded-lg text-sm font-medium"
                  >
                    Wait for More Files
                  </button>
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default ReceiverDashboard;
