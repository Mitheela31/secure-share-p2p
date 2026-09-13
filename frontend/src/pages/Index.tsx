import React, { useState, useEffect, useRef } from 'react';
import { CryptoProvider } from '@/contexts/CryptoContext';
import AuthPage from '@/components/AuthPage';
import RoleSelection from '@/components/RoleSelection';
import SenderDashboard from '@/components/SenderDashboard';
import ReceiverDashboard from '@/components/ReceiverDashboard';
import { TransferRecord } from '@/components/TransferHistory';
import { authService, User } from '@/lib/authService';
import { userService } from '@/lib/userService';

type AppState = 'auth' | 'role-select' | 'sender' | 'receiver';

// ---------------------------------------------------------------------------
// HEARTBEAT CONFIGURATION
// ---------------------------------------------------------------------------
// The frontend pings /api/v1/users/heartbeat/ every HEARTBEAT_INTERVAL ms.
// The backend considers a user offline after ONLINE_THRESHOLD_SECONDS (60 s)
// without a heartbeat.  Sending every 30 s means one missed beat is allowed
// before the user disappears from the online list.
// ---------------------------------------------------------------------------
const HEARTBEAT_INTERVAL_MS = 30_000; // 30 seconds

const IndexContent = () => {
  const [appState, setAppState] = useState<AppState>('auth');
  const [currentUser, setCurrentUser] = useState<User | null>(null);
  const [transfers, setTransfers] = useState<TransferRecord[]>([]);

  // Keep a ref so the interval callback always has the latest user value
  // without needing to re-create the interval on every render.
  const currentUserRef = useRef<User | null>(null);
  currentUserRef.current = currentUser;

  /**
   * HEARTBEAT MECHANISM
   *
   * Why this is needed:
   *   The backend stores a `last_seen` timestamp, not a boolean flag.
   *   A user is "online" only while last_seen >= now() - 60 s.
   *   Without heartbeats the timestamp goes stale and the user automatically
   *   disappears from the online list — no explicit logout required.
   *
   * What we do here:
   *   1. Send an immediate heartbeat on login.
   *   2. Send a heartbeat every 30 s (setInterval).
   *   3. Pause heartbeats when the tab is hidden (Page Visibility API) —
   *      this conserves resources; the user will fall offline after 60 s anyway.
   *   4. Best-effort heartbeat on logout (then clear the interval).
   */
  useEffect(() => {
    if (!currentUser) return;

    // 1. Immediate heartbeat so the user shows as online right away.
    userService.heartbeat().catch((err) =>
      console.debug('[Heartbeat] Initial heartbeat failed:', err)
    );

    // 2. Periodic heartbeat every 30 seconds.
    const intervalId = setInterval(() => {
      // Only send if the page is visible — if the tab is hidden or the
      // laptop is asleep the heartbeat will be skipped, and the user
      // will naturally expire from the online list after 60 s.
      if (document.visibilityState === 'visible' && currentUserRef.current) {
        userService.heartbeat().catch((err) =>
          console.debug('[Heartbeat] Periodic heartbeat failed:', err)
        );
      }
    }, HEARTBEAT_INTERVAL_MS);

    // 3. When the tab becomes visible again, send an immediate heartbeat
    //    so the user re-appears online without waiting 30 s.
    const handleVisibilityChange = () => {
      if (document.visibilityState === 'visible' && currentUserRef.current) {
        userService.heartbeat().catch(() => {});
      }
    };
    document.addEventListener('visibilitychange', handleVisibilityChange);

    // 4. Cleanup: clear interval when user logs out or component unmounts.
    return () => {
      clearInterval(intervalId);
      document.removeEventListener('visibilitychange', handleVisibilityChange);
    };
  }, [currentUser]);

  const handleLogin = (user: User) => {
    setCurrentUser(user);
    setAppState('role-select');
  };

  const handleSelectRole = (role: 'sender' | 'receiver') => {
    setAppState(role);
  };

  const handleLogout = async () => {
    await authService.logout();
    setCurrentUser(null);
    setAppState('auth');
    setTransfers([]);
  };

  const handleBackToRoleSelect = () => {
    setAppState('role-select');
  };

  const handleNewTransfer = (transfer: TransferRecord) => {
    setTransfers(prev => [transfer, ...prev]);
  };

  return (
    <div className="min-h-screen">
      {appState === 'auth' && (
        <AuthPage onLogin={handleLogin} />
      )}
      
      {appState === 'role-select' && currentUser && (
        <RoleSelection 
          username={currentUser.username} 
          onSelectRole={handleSelectRole}
          onLogout={handleLogout}
        />
      )}
      
      {appState === 'sender' && currentUser && (
        <SenderDashboard 
          username={currentUser.username}
          userId={currentUser.id}
          onBack={handleBackToRoleSelect}
          onLogout={handleLogout}
          transfers={transfers}
          onNewTransfer={handleNewTransfer}
        />
      )}
      
      {appState === 'receiver' && currentUser && (
        <ReceiverDashboard 
          username={currentUser.username}
          onBack={handleBackToRoleSelect}
          onLogout={handleLogout}
          transfers={transfers}
          onNewTransfer={handleNewTransfer}
        />
      )}
    </div>
  );
};

const Index = () => {
  return (
    <CryptoProvider>
      <IndexContent />
    </CryptoProvider>
  );
};

export default Index;
