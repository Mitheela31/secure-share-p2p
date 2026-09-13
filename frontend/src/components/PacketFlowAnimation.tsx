import React, { useState, useEffect } from 'react';
import { Lock, ArrowRight, Shield, CheckCircle2 } from 'lucide-react';

interface PacketFlowAnimationProps {
  isActive: boolean;
  senderName: string;
  receiverName: string;
  currentPacket?: number;
  totalPackets?: number;
}

const PacketFlowAnimation: React.FC<PacketFlowAnimationProps> = ({
  isActive,
  senderName,
  receiverName,
  currentPacket = 0,
  totalPackets = 5
}) => {
  const [packets, setPackets] = useState<number[]>([]);

  useEffect(() => {
    if (!isActive) {
      setPackets([]);
      return;
    }

    // Add a new packet every 400ms
    const interval = setInterval(() => {
      setPackets(prev => {
        const newPackets = [...prev, Date.now()];
        // Keep only the last 5 packets
        return newPackets.slice(-5);
      });
    }, 400);

    return () => clearInterval(interval);
  }, [isActive]);

  // Remove packets after animation completes
  useEffect(() => {
    if (packets.length > 0) {
      const timeout = setTimeout(() => {
        setPackets(prev => prev.slice(1));
      }, 1500);
      return () => clearTimeout(timeout);
    }
  }, [packets]);

  return (
    <div className="relative py-8">
      {/* Channel line */}
      <div className="absolute inset-x-0 top-1/2 h-1 bg-gradient-to-r from-primary via-secondary to-primary opacity-30 rounded-full" />
      
      {/* Encrypted channel indicator */}
      <div className="absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 z-10">
        <div className={`
          p-2 rounded-lg border transition-all duration-300
          ${isActive 
            ? 'bg-success/20 border-success/50 animate-pulse' 
            : 'bg-muted border-border'
          }
        `}>
          {isActive ? (
            <Shield className="w-5 h-5 text-success" />
          ) : (
            <Lock className="w-5 h-5 text-muted-foreground" />
          )}
        </div>
      </div>

      {/* Sender endpoint */}
      <div className="absolute left-0 top-1/2 -translate-y-1/2 flex items-center gap-2">
        <div className="w-10 h-10 rounded-lg bg-primary/20 flex items-center justify-center">
          <span className="text-primary font-bold">{senderName[0]}</span>
        </div>
        {isActive && (
          <ArrowRight className="w-4 h-4 text-primary animate-pulse" />
        )}
      </div>

      {/* Receiver endpoint */}
      <div className="absolute right-0 top-1/2 -translate-y-1/2 flex items-center gap-2">
        {isActive && (
          <ArrowRight className="w-4 h-4 text-secondary animate-pulse" />
        )}
        <div className="w-10 h-10 rounded-lg bg-secondary/20 flex items-center justify-center">
          <span className="text-secondary font-bold">{receiverName[0]}</span>
        </div>
      </div>

      {/* Animated packets */}
      {packets.map((id, index) => (
        <div
          key={id}
          className="absolute top-1/2 -translate-y-1/2 animate-data-flow"
          style={{
            left: '15%',
            animationDelay: `${index * 100}ms`,
          }}
        >
          <div className="w-6 h-6 rounded bg-gradient-cyber flex items-center justify-center">
            <Lock className="w-3 h-3 text-primary-foreground" />
          </div>
        </div>
      ))}

      {/* Status text */}
      <div className="absolute -bottom-6 left-1/2 -translate-x-1/2 whitespace-nowrap">
        {isActive ? (
          <div className="flex items-center gap-2 text-xs">
            <div className="w-2 h-2 rounded-full bg-success pulse-dot" />
            <span className="text-success font-medium">End-to-End Encrypted Channel Active</span>
          </div>
        ) : (
          <span className="text-xs text-muted-foreground">Waiting for connection...</span>
        )}
      </div>
    </div>
  );
};

export default PacketFlowAnimation;
