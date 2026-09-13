import React from 'react';
import { Shield, Wifi, Lock, Activity } from 'lucide-react';
import { useCrypto } from '@/contexts/CryptoContext';

interface GlobalBannerProps {
  username: string;
}

const GlobalBanner: React.FC<GlobalBannerProps> = ({ username }) => {
  const { secureChannelActive, sessionKeyGenerated, logs } = useCrypto();

  return (
    <div className="glass-card cyber-border animated-border mb-6 p-4">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        {/* User info */}
        <div className="flex items-center gap-4">
          <div className="w-12 h-12 rounded-xl bg-gradient-cyber flex items-center justify-center text-primary-foreground font-bold text-lg">
            {username[0].toUpperCase()}
          </div>
          <div>
            <p className="font-bold">{username}</p>
            <div className="flex items-center gap-2 text-sm">
              <div className="w-2 h-2 rounded-full bg-success pulse-dot" />
              <span className="text-success">Secure Session Active</span>
            </div>
          </div>
        </div>

        {/* Status indicators */}
        <div className="flex flex-wrap items-center gap-3">
          <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-success/10 border border-success/30">
            <Shield className="w-4 h-4 text-success" />
            <span className="text-xs font-medium text-success">Secure P2P Session Active</span>
          </div>
          
          <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-primary/10 border border-primary/30">
            <Lock className="w-4 h-4 text-primary" />
            <span className="text-xs font-medium text-primary">E2E Encrypted</span>
          </div>

          <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-secondary/10 border border-secondary/30">
            <Activity className="w-4 h-4 text-secondary" />
            <span className="text-xs font-medium text-secondary font-mono">{logs.length} ops</span>
          </div>
        </div>
      </div>
    </div>
  );
};

export default GlobalBanner;
