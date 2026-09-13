import React from 'react';
import { Lock, Unlock, CheckCircle2, Loader2, Package } from 'lucide-react';
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";

interface ChunkProgressProps {
  currentChunk: number;
  totalChunks: number;
  phase: 'encrypting' | 'transmitting' | 'decrypting';
  algorithm?: string;
}

const ChunkProgress: React.FC<ChunkProgressProps> = ({
  currentChunk,
  totalChunks,
  phase,
  algorithm = 'AES-256-GCM'
}) => {
  const getPhaseIcon = () => {
    switch (phase) {
      case 'encrypting':
        return <Lock className="w-4 h-4" />;
      case 'transmitting':
        return <Package className="w-4 h-4" />;
      case 'decrypting':
        return <Unlock className="w-4 h-4" />;
    }
  };

  const getPhaseColor = () => {
    switch (phase) {
      case 'encrypting':
        return 'text-primary';
      case 'transmitting':
        return 'text-secondary';
      case 'decrypting':
        return 'text-success';
    }
  };

  const getPhaseLabel = () => {
    switch (phase) {
      case 'encrypting':
        return 'Encrypting';
      case 'transmitting':
        return 'Transmitting';
      case 'decrypting':
        return 'Decrypting';
    }
  };

  return (
    <TooltipProvider>
      <div className="space-y-4">
        {/* Phase header */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <span className={getPhaseColor()}>{getPhaseIcon()}</span>
            <span className={`font-medium ${getPhaseColor()}`}>
              {getPhaseLabel()} Chunk {currentChunk}/{totalChunks}
            </span>
          </div>
          <Tooltip>
            <TooltipTrigger asChild>
              <span className="px-2 py-1 rounded bg-muted text-muted-foreground text-xs font-mono cursor-help">
                {algorithm}
              </span>
            </TooltipTrigger>
            <TooltipContent>
              <p className="text-xs">
                {algorithm.includes('AES-256-GCM') && 
                  'AES-256 with Galois/Counter Mode: Provides both encryption and authentication'}
              </p>
            </TooltipContent>
          </Tooltip>
        </div>

        {/* Chunk visualization */}
        <div className="grid grid-cols-5 gap-2">
          {Array.from({ length: totalChunks }).map((_, index) => {
            const chunkNum = index + 1;
            const isComplete = chunkNum < currentChunk;
            const isActive = chunkNum === currentChunk;
            const isPending = chunkNum > currentChunk;

            return (
              <Tooltip key={index}>
                <TooltipTrigger asChild>
                  <div
                    className={`
                      relative h-10 rounded-lg flex items-center justify-center transition-all duration-300 cursor-help
                      ${isComplete ? 'bg-success/20 border border-success/50' : ''}
                      ${isActive ? 'bg-primary/20 border border-primary/50 animate-pulse' : ''}
                      ${isPending ? 'bg-muted/50 border border-border' : ''}
                    `}
                  >
                    {isComplete && (
                      <CheckCircle2 className="w-4 h-4 text-success" />
                    )}
                    {isActive && (
                      <Loader2 className="w-4 h-4 text-primary animate-spin" />
                    )}
                    {isPending && (
                      <span className="text-xs text-muted-foreground">{chunkNum}</span>
                    )}

                    {/* Progress indicator for active chunk */}
                    {isActive && (
                      <div className="absolute bottom-0 left-0 right-0 h-1 bg-muted rounded-b-lg overflow-hidden">
                        <div 
                          className="h-full bg-primary animate-pulse"
                          style={{ width: '50%' }}
                        />
                      </div>
                    )}
                  </div>
                </TooltipTrigger>
                <TooltipContent>
                  <p className="text-xs">
                    Chunk {chunkNum}: {isComplete ? 'Complete' : isActive ? 'Processing...' : 'Pending'}
                  </p>
                </TooltipContent>
              </Tooltip>
            );
          })}
        </div>

        {/* Data flow animation */}
        <div className="relative h-2 bg-muted rounded-full overflow-hidden">
          <div 
            className="absolute inset-y-0 left-0 bg-gradient-to-r from-primary via-secondary to-primary rounded-full transition-all duration-300"
            style={{ width: `${(currentChunk / totalChunks) * 100}%` }}
          />
          <div 
            className="absolute inset-y-0 left-0 w-full bg-gradient-to-r from-transparent via-white/20 to-transparent animate-shimmer"
            style={{ backgroundSize: '200% 100%' }}
          />
        </div>

        {/* Chunk details */}
        <div className="text-xs text-muted-foreground text-center">
          {phase === 'encrypting' && `Encrypting data block ${currentChunk} with session key...`}
          {phase === 'transmitting' && `Sending encrypted chunk ${currentChunk} over P2P channel...`}
          {phase === 'decrypting' && `Decrypting data block ${currentChunk} with session key...`}
        </div>
      </div>
    </TooltipProvider>
  );
};

export default ChunkProgress;
