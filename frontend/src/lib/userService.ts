/**
 * User Service
 * 
 * Handles user listing and user-related operations.
 * 
 * REPLACES MOCK DATA IN:
 * - SenderDashboard.tsx: MOCK_RECEIVERS array (lines 32-38)
 * - ReceiverDashboard.tsx: Mock sender data
 * 
 * API ENDPOINTS:
 * - GET /api/v1/users/ - List all users
 * - GET /api/v1/users/online/ - List online users
 * - GET /api/v1/users/<id>/ - Get user details
 */

import api, { handleApiError } from './api';
import { User } from './authService';

// Types
export interface UserListResponse {
  count: number;
  next: string | null;
  previous: string | null;
  results: User[];
}

// User service functions
export const userService = {
  /**
   * Get all users (excluding current user)
   * 
   * REPLACES: MOCK_RECEIVERS in SenderDashboard.tsx
   * 
   * Frontend mapping:
   * - User.id → Receiver.id
   * - User.username → Receiver.name
   * - User.is_online → Receiver.online
   * 
   * @example
   * const users = await userService.getUsers();
   * const receivers = users.map(u => ({
   *   id: u.id.toString(),
   *   name: u.username,
   *   online: u.is_online
   * }));
   */
  async getUsers(search?: string): Promise<User[]> {
    try {
      const params = new URLSearchParams();
      if (search) {
        params.append('search', search);
      }
      
      const response = await api.get<UserListResponse>(`/users/?${params.toString()}`);
      return response.data.results;
    } catch (error) {
      throw handleApiError(error as any);
    }
  },

  /**
   * Get only online users
   * 
   * Use this for showing available receivers in SenderDashboard
   */
  async getOnlineUsers(): Promise<User[]> {
    try {
      const response = await api.get<UserListResponse>('/users/online/');
      return response.data.results;
    } catch (error) {
      throw handleApiError(error as any);
    }
  },

  /**
   * Get users filtered by online status
   */
  async getUsersByOnlineStatus(isOnline: boolean): Promise<User[]> {
    try {
      const response = await api.get<UserListResponse>(`/users/?is_online=${isOnline}`);
      return response.data.results;
    } catch (error) {
      throw handleApiError(error as any);
    }
  },

  /**
   * Get specific user by ID
   */
  async getUserById(id: number): Promise<User> {
    try {
      const response = await api.get<User>(`/users/${id}/`);
      return response.data;
    } catch (error) {
      throw handleApiError(error as any);
    }
  },

  /**
   * Send heartbeat to keep user online status active.
   *
   * The backend stamps user.last_seen = now() and returns the current count
   * of online users.  A user whose last_seen is > 60 s ago automatically
   * falls off the online list — no explicit offline call is needed.
   *
   * Call cadence: every 30 s (see Index.tsx).
   *
   * @example
   * useEffect(() => {
   *   const id = setInterval(() => userService.heartbeat().catch(() => {}), 30_000);
   *   return () => clearInterval(id);
   * }, [currentUser]);
   */
  async heartbeat(): Promise<{ is_online: boolean; last_seen: string; online_users_count: number }> {
    try {
      const response = await api.post<{
        message: string;
        is_online: boolean;
        last_seen: string;
        online_users_count: number;
      }>('/users/heartbeat/');
      return response.data;
    } catch (error) {
      throw handleApiError(error as any);
    }
  },

  /**
   * Manually clean up stale users
   * 
   * @param thresholdMinutes - How many minutes of inactivity before marking offline
   */
  async cleanupStaleUsers(thresholdMinutes: number = 5): Promise<{ users_marked_offline: number }> {
    try {
      const response = await api.post<{ 
        message: string; 
        users_marked_offline: number; 
        threshold_minutes: number 
      }>('/users/cleanup/', { threshold_minutes: thresholdMinutes });
      return { users_marked_offline: response.data.users_marked_offline };
    } catch (error) {
      throw handleApiError(error as any);
    }
  },
};

/**
 * Helper function to convert API User to frontend Receiver format
 * 
 * Use this to replace MOCK_RECEIVERS:
 * 
 * // Before (mock):
 * const MOCK_RECEIVERS = [
 *   { id: '1', name: 'Alice_Secure', online: true },
 *   ...
 * ];
 * 
 * // After (real API):
 * const [receivers, setReceivers] = useState<Receiver[]>([]);
 * useEffect(() => {
 *   userService.getUsers().then(users => {
 *     setReceivers(users.map(userToReceiver));
 *   });
 * }, []);
 */
export const userToReceiver = (user: User): { id: string; name: string; online: boolean } => ({
  id: user.id.toString(),
  name: user.username,
  online: user.is_online,
});

export default userService;
