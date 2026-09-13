import React from 'react';
import { Send, Download, Shield, ArrowRight, Lock, Key, Wifi } from 'lucide-react';
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";

interface RoleSelectionProps {
  username: string;
  onSelectRole: (role: 'sender' | 'receiver') => void;
  onLogout: () => void;
}

const RoleSelection: React.FC<RoleSelectionProps> = ({ username, onSelectRole, onLogout }) => {
  return (
    <TooltipProvider>
      <div className="min-h-screen flex items-center justify-center p-4 relative overflow-hidden">
        {/* Background effects */}
        <div className="absolute inset-0 bg-cyber-grid bg-grid opacity-30" />
        <div className="absolute top-1/3 left-1/3 w-[500px] h-[500px] bg-primary/5 rounded-full blur-3xl" />
        <div className="absolute bottom-1/3 right-1/3 w-[500px] h-[500px] bg-secondary/5 rounded-full blur-3xl" />

        <div className="w-full max-w-4xl relative z-10">
          {/* Header */}
          <div className="text-center mb-12 animate-fade-in-up">
            {/* Secure session banner */}
            <div className="inline-flex items-center gap-3 px-6 py-3 rounded-xl bg-success/10 border border-success/30 mb-8">
              <div className="w-3 h-3 rounded-full bg-success pulse-dot" />
              <Shield className="w-5 h-5 text-success" />
              <span className="font-medium text-success">Secure P2P Session Active</span>
            </div>
            
            <h1 className="text-4xl md:text-5xl font-bold mb-4">
              Welcome, <span className="text-gradient">{username}</span>
            </h1>
            <p className="text-xl text-muted-foreground mb-6">
              Select your role to begin secure file sharing
            </p>

            {/* Security info badges */}
            <div className="flex flex-wrap items-center justify-center gap-3">
              <Tooltip>
                <TooltipTrigger asChild>
                  <div className="flex items-center gap-2 px-4 py-2 rounded-lg bg-muted/50 border border-border cursor-help">
                    <Key className="w-4 h-4 text-primary" />
                    <span className="text-sm text-muted-foreground">ECDH P-256</span>
                  </div>
                </TooltipTrigger>
                <TooltipContent className="max-w-xs">
                  <p className="text-xs">
                    Elliptic Curve Diffie-Hellman key exchange using the P-256 curve. 
                    Enables secure key agreement between peers.
                  </p>
                </TooltipContent>
              </Tooltip>
              
              <Tooltip>
                <TooltipTrigger asChild>
                  <div className="flex items-center gap-2 px-4 py-2 rounded-lg bg-muted/50 border border-border cursor-help">
                    <Lock className="w-4 h-4 text-secondary" />
                    <span className="text-sm text-muted-foreground">AES-256-GCM</span>
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
                  <div className="flex items-center gap-2 px-4 py-2 rounded-lg bg-muted/50 border border-border cursor-help">
                    <Wifi className="w-4 h-4 text-success" />
                    <span className="text-sm text-muted-foreground">P2P Secure</span>
                  </div>
                </TooltipTrigger>
                <TooltipContent className="max-w-xs">
                  <p className="text-xs">
                    Peer-to-peer connection with end-to-end encryption. 
                    Data never passes through intermediate servers.
                  </p>
                </TooltipContent>
              </Tooltip>
            </div>
          </div>

          {/* Role cards */}
          <div className="grid md:grid-cols-2 gap-6 mb-8 stagger-children">
            {/* Sender card */}
            <button
              onClick={() => onSelectRole('sender')}
              className="glass-card cyber-border group p-8 text-left transition-all duration-300 hover:scale-[1.02] hover:glow-primary"
            >
              <div className="flex items-start justify-between mb-6">
                <div className="w-16 h-16 rounded-2xl bg-gradient-cyber flex items-center justify-center group-hover:animate-shield">
                  <Send className="w-8 h-8 text-primary-foreground" />
                </div>
                <ArrowRight className="w-6 h-6 text-muted-foreground group-hover:text-primary group-hover:translate-x-1 transition-all" />
              </div>
              <h2 className="text-2xl font-bold mb-3 group-hover:text-gradient transition-all">
                Send Files
              </h2>
              <p className="text-muted-foreground mb-6">
                Share files securely with end-to-end encryption. Select a receiver and transfer files with complete privacy.
              </p>
              <div className="flex flex-wrap gap-2">
                <span className="px-3 py-1 rounded-full bg-primary/10 text-primary text-xs font-medium">
                  Key Exchange
                </span>
                <span className="px-3 py-1 rounded-full bg-secondary/10 text-secondary text-xs font-medium">
                  Encrypt Files
                </span>
                <span className="px-3 py-1 rounded-full bg-success/10 text-success text-xs font-medium">
                  Secure Transfer
                </span>
              </div>
            </button>

            {/* Receiver card */}
            <button
              onClick={() => onSelectRole('receiver')}
              className="glass-card cyber-border group p-8 text-left transition-all duration-300 hover:scale-[1.02] hover:glow-secondary"
            >
              <div className="flex items-start justify-between mb-6">
                <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-secondary to-secondary/70 flex items-center justify-center group-hover:animate-shield">
                  <Download className="w-8 h-8 text-secondary-foreground" />
                </div>
                <ArrowRight className="w-6 h-6 text-muted-foreground group-hover:text-secondary group-hover:translate-x-1 transition-all" />
              </div>
              <h2 className="text-2xl font-bold mb-3 group-hover:text-gradient transition-all">
                Receive Files
              </h2>
              <p className="text-muted-foreground mb-6">
                Accept incoming file transfers from trusted senders. Files are automatically decrypted upon receipt.
              </p>
              <div className="flex flex-wrap gap-2">
                <span className="px-3 py-1 rounded-full bg-primary/10 text-primary text-xs font-medium">
                  Accept Requests
                </span>
                <span className="px-3 py-1 rounded-full bg-secondary/10 text-secondary text-xs font-medium">
                  Decrypt Files
                </span>
                <span className="px-3 py-1 rounded-full bg-success/10 text-success text-xs font-medium">
                  Verify Integrity
                </span>
              </div>
            </button>
          </div>

          {/* Security note */}
          <div className="text-center mb-6">
            <p className="text-xs text-muted-foreground">
              🔐 All cryptographic operations are simulated for demonstration • Private keys never leave your device
            </p>
          </div>

          {/* Logout button */}
          <div className="text-center animate-fade-in-up" style={{ animationDelay: '0.4s' }}>
            <button
              onClick={onLogout}
              className="text-muted-foreground hover:text-foreground transition-colors text-sm"
            >
              Sign out of this session
            </button>
          </div>
        </div>
      </div>
    </TooltipProvider>
  );
};

export default RoleSelection;
