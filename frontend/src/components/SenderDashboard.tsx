import React, { useState, useEffect } from 'react';
import { 
  Send, 
  ArrowLeft, 
  Shield, 
  User, 
  CheckCircle2,
  Clock,
  Wifi,
  WifiOff,
  Loader2,
  History,
  Terminal,
  Key,
  RefreshCw
} from 'lucide-react';
import { useCrypto } from '@/contexts/CryptoContext';
import FileTransfer from './FileTransfer';
import TransferHistory, { TransferRecord } from './TransferHistory';
import GlobalBanner from './GlobalBanner';
import SecurityLog from './SecurityLog';
import KeyExchangeVisualizer from './KeyExchangeVisualizer';
import { userService } from '@/lib/userService';

interface SenderDashboardProps {
  username: string;
  userId: number;
  onBack: () => void;
  onLogout: () => void;
  transfers: TransferRecord[];
  onNewTransfer: (transfer: TransferRecord) => void;
}

interface Receiver {
  id: string;
  name: string;
  online: boolean;
}

type ConnectionState = 'idle' | 'requesting' | 'key-exchange' | 'connected' | 'transferring' | 'complete';

const SenderDashboard: React.FC<SenderDashboardProps> = ({ 
  username,
  userId,
  onBack, 
  onLogout,
  transfers,
  onNewTransfer
}) => {
  const [selectedReceiver, setSelectedReceiver] = useState<Receiver | null>(null);
  const [connectionState, setConnectionState] = useState<ConnectionState>('idle');
  const [showHistory, setShowHistory] = useState(false);
  const [showSecurityLog, setShowSecurityLog] = useState(true);
  const [receivers, setReceivers] = useState<Receiver[]>([]);
  const [loadingReceivers, setLoadingReceivers] = useState(true);

  const { addLog, resetCryptoState, setConnectionEstablished, setSecureChannelActive } = useCrypto();

  // Fetch receivers from API
  const fetchReceivers = async () => {
    setLoadingReceivers(true);
    try {
      const users = await userService.getUsers();
      // Filter out current user and map to Receiver format
      const receiversList = users
        .filter(u => u.id !== userId)
        .map(u => ({
          id: u.id.toString(),
          name: u.username,
          online: u.is_online,
        }));
      setReceivers(receiversList);
    } catch (error) {
      console.error('Failed to fetch receivers:', error);
      // Fallback to empty list
      setReceivers([]);
    } finally {
      setLoadingReceivers(false);
    }
  };

  useEffect(() => {
    fetchReceivers();
    
    // Periodically refresh receivers list to get updated online status
    const refreshInterval = setInterval(fetchReceivers, 15000); // Every 15 seconds
    
    return () => clearInterval(refreshInterval);
  }, [userId]);

  const handleConnect = async (receiver: Receiver) => {
    setSelectedReceiver(receiver);
    setConnectionState('requesting');
    
    addLog({
      type: 'network',
      category: 'connection',
      message: `Initiating connection request to ${receiver.name}...`,
    });
    
    // Simulate connection request
    await new Promise(r => setTimeout(r, 1500));
    
    addLog({
      type: 'success',
      category: 'connection',
      message: `Connection request accepted by ${receiver.name}`,
    });

    addLog({
      type: 'info',
      category: 'connection',
      message: 'Initiating secure key exchange protocol...',
    });
    
    setConnectionState('key-exchange');
  };

  const handleKeyExchangeComplete = () => {
    setConnectionEstablished(true);
    setSecureChannelActive(true);
    setConnectionState('connected');
  };

  const handleTransferComplete = (fileName: string, fileSize: string, fileId: number, transferUuid: string) => {
    const newTransfer: TransferRecord = {
      id: Date.now().toString(),
      transferUuid,
      fileId,
      fileName,
      fileSize,
      sender: username,
      receiver: selectedReceiver?.name || '',
      timestamp: new Date(),
      type: 'sent',
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
      message: `Receiver ${selectedReceiver?.name} successfully received and decrypted the file`,
    });
  };

  const resetConnection = () => {
    setSelectedReceiver(null);
    setConnectionState('idle');
    resetCryptoState();
  };

  return (
    <div className="min-h-screen p-4 md:p-8 relative overflow-hidden">
      {/* Background effects */}
      <div className="absolute inset-0 bg-cyber-grid bg-grid opacity-20" />
      <div className="absolute top-0 right-0 w-[600px] h-[600px] bg-primary/5 rounded-full blur-3xl" />
      
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
                <Send className="w-5 h-5 text-primary" />
                <h1 className="text-2xl font-bold">Sender Dashboard</h1>
              </div>
              <div className="flex items-center gap-2 text-sm text-muted-foreground">
                <User className="w-4 h-4" />
                <span>{username}</span>
                <span className="w-2 h-2 rounded-full bg-success" />
                <span className="text-success">Online</span>
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
                  ? 'border-primary bg-primary/10 text-primary' 
                  : 'border-border hover:border-primary/50'
              }`}
            >
              <History className="w-4 h-4" />
              <span className="hidden sm:inline">History</span>
              {transfers.length > 0 && (
                <span className="px-1.5 py-0.5 rounded-full bg-primary text-primary-foreground text-xs">
                  {transfers.filter(t => t.type === 'sent').length}
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
            <TransferHistory transfers={transfers.filter(t => t.type === 'sent')} currentUser={username} />
          </div>
        ) : (
          <div className="grid lg:grid-cols-3 gap-6">
            {/* Main content area */}
            <div className="lg:col-span-2 space-y-6">
              {/* Receiver list */}
              <div className="glass-card cyber-border p-6">
                <div className="flex items-center justify-between mb-1">
                  <h2 className="font-bold text-lg">Available Receivers</h2>
                  <button
                    onClick={fetchReceivers}
                    disabled={loadingReceivers}
                    className="p-2 rounded-lg hover:bg-muted transition-colors disabled:opacity-50"
                    title="Refresh receivers"
                  >
                    <RefreshCw className={`w-4 h-4 ${loadingReceivers ? 'animate-spin' : ''}`} />
                  </button>
                </div>
                <p className="text-muted-foreground text-sm mb-6">
                  Select a receiver to establish a secure P2P connection
                </p>

                {loadingReceivers ? (
                  <div className="flex items-center justify-center py-12">
                    <Loader2 className="w-8 h-8 animate-spin text-primary" />
                  </div>
                ) : receivers.length === 0 ? (
                  <div className="text-center py-12 text-muted-foreground">
                    <User className="w-12 h-12 mx-auto mb-4 opacity-50" />
                    <p>No other users available</p>
                    <p className="text-sm">Register more users to start transferring files</p>
                  </div>
                ) : (
                <div className="grid sm:grid-cols-2 gap-4">
                  {receivers.map((receiver) => (
                    <div
                      key={receiver.id}
                      className={`
                        p-4 rounded-xl border transition-all duration-300
                        ${selectedReceiver?.id === receiver.id 
                          ? 'border-primary bg-primary/5 glow-primary' 
                          : 'border-border hover:border-primary/50 bg-muted/30'
                        }
                        ${!receiver.online ? 'opacity-60' : ''}
                      `}
                    >
                      <div className="flex items-start justify-between mb-3">
                        <div className="flex items-center gap-3">
                          <div className="w-10 h-10 rounded-full bg-gradient-cyber flex items-center justify-center text-primary-foreground font-bold">
                            {receiver.name[0]}
                          </div>
                          <div>
                            <p className="font-medium">{receiver.name}</p>
                            <div className="flex items-center gap-1.5 text-xs">
                              {receiver.online ? (
                                <>
                                  <Wifi className="w-3 h-3 text-success" />
                                  <span className="text-success">Online</span>
                                </>
                              ) : (
                                <>
                                  <WifiOff className="w-3 h-3 text-muted-foreground" />
                                  <span className="text-muted-foreground">Offline</span>
                                </>
                              )}
                            </div>
                          </div>
                        </div>
                        <Shield className="w-4 h-4 text-success" />
                      </div>

                      <button
                        onClick={() => handleConnect(receiver)}
                        disabled={!receiver.online || connectionState !== 'idle'}
                        className={`
                          w-full py-2 rounded-lg text-sm font-medium transition-all
                          ${selectedReceiver?.id === receiver.id 
                            ? 'bg-primary text-primary-foreground' 
                            : 'bg-muted hover:bg-primary/20 text-foreground'
                          }
                          disabled:opacity-50 disabled:cursor-not-allowed
                        `}
                      >
                        {selectedReceiver?.id === receiver.id 
                          ? 'Selected' 
                          : receiver.online 
                            ? 'Connect' 
                            : 'Unavailable'
                        }
                      </button>
                    </div>
                  ))}
                </div>
                )}
              </div>

              {/* Security Log */}
              {showSecurityLog && (
                <div className="animate-fade-in-up">
                  <SecurityLog maxHeight="250px" />
                </div>
              )}
            </div>

            {/* Connection status / Key Exchange / File transfer */}
            <div className="lg:col-span-1 space-y-6">
              {connectionState === 'idle' && (
                <div className="glass-card cyber-border p-6 text-center">
                  <div className="w-16 h-16 mx-auto rounded-2xl bg-muted flex items-center justify-center mb-4">
                    <Shield className="w-8 h-8 text-muted-foreground" />
                  </div>
                  <h3 className="font-bold mb-2">No Connection</h3>
                  <p className="text-muted-foreground text-sm">
                    Select an online receiver to establish a secure P2P connection
                  </p>
                </div>
              )}

              {connectionState === 'requesting' && (
                <div className="glass-card cyber-border animated-border p-6 text-center">
                  <div className="w-16 h-16 mx-auto rounded-2xl bg-primary/20 flex items-center justify-center mb-4">
                    <Loader2 className="w-8 h-8 text-primary animate-spin" />
                  </div>
                  <h3 className="font-bold mb-2">Requesting Connection</h3>
                  <p className="text-muted-foreground text-sm">
                    Waiting for <span className="text-primary">{selectedReceiver?.name}</span> to accept...
                  </p>
                  <div className="mt-4 flex items-center justify-center gap-2 text-xs text-muted-foreground">
                    <Clock className="w-3 h-3" />
                    <span>Connection request sent</span>
                  </div>
                  
                  {/* Connection timeline */}
                  <div className="mt-6 space-y-2 text-left">
                    <div className="flex items-center gap-3 p-2 rounded-lg bg-success/10">
                      <CheckCircle2 className="w-4 h-4 text-success" />
                      <span className="text-sm text-success">Connection Request Sent</span>
                    </div>
                    <div className="flex items-center gap-3 p-2 rounded-lg bg-primary/10">
                      <Loader2 className="w-4 h-4 text-primary animate-spin" />
                      <span className="text-sm text-primary">Awaiting Acceptance</span>
                    </div>
                    <div className="flex items-center gap-3 p-2 rounded-lg">
                      <div className="w-4 h-4 rounded-full border-2 border-muted" />
                      <span className="text-sm text-muted-foreground">Secure Channel Established</span>
                    </div>
                  </div>
                </div>
              )}

              {connectionState === 'key-exchange' && selectedReceiver && (
                <KeyExchangeVisualizer
                  senderName={username}
                  receiverName={selectedReceiver.name}
                  onComplete={handleKeyExchangeComplete}
                />
              )}

              {connectionState === 'connected' && selectedReceiver && (
                <FileTransfer
                  receiverName={selectedReceiver.name}
                  receiverId={parseInt(selectedReceiver.id, 10)}
                  onTransferComplete={handleTransferComplete}
                  onCancel={resetConnection}
                />
              )}

              {connectionState === 'complete' && (
                <div className="glass-card cyber-border p-6 text-center">
                  <div className="w-16 h-16 mx-auto rounded-2xl bg-success/20 flex items-center justify-center mb-4">
                    <CheckCircle2 className="w-8 h-8 text-success" />
                  </div>
                  <h3 className="font-bold text-success mb-2">Transfer Complete!</h3>
                  <p className="text-muted-foreground text-sm mb-4">
                    File was successfully sent to <span className="text-primary">{selectedReceiver?.name}</span>
                  </p>
                  <p className="text-xs text-success mb-4">
                    ✓ Receiver successfully received and decrypted the file
                  </p>
                  <button
                    onClick={resetConnection}
                    className="px-6 py-2 cyber-btn text-primary-foreground rounded-lg text-sm font-medium"
                  >
                    Send Another File
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

export default SenderDashboard;
