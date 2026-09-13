/**
 * Authentication Service
 * 
 * Handles user authentication, registration, and session management.
 * 
 * REPLACES MOCK DATA IN:
 * - AuthPage.tsx: Mock login/register logic
 * - App.tsx: User session state
 * 
 * API ENDPOINTS:
 * - POST /api/v1/auth/register/ - User registration
 * - POST /api/v1/auth/login/ - User login (returns JWT)
 * - POST /api/v1/auth/logout/ - User logout
 * - GET /api/v1/auth/profile/ - Get current user profile
 * - PUT /api/v1/auth/profile/ - Update profile
 * - POST /api/v1/auth/password/change/ - Change password
 */

import api, { setTokens, clearTokens, handleApiError, ApiError } from './api';

// Types
export interface User {
  id: number;
  username: string;
  email: string;
  first_name: string;
  last_name: string;
  /**
   * Computed server-side: true only if last_seen >= now() - 60 s.
   * Never trust a cached copy of this field — always re-fetch from the
   * /users/online/ or /users/?is_online=true endpoints for current state.
   */
  is_online: boolean;
  /**
   * Timestamp of the last heartbeat received from this user.
   * Null if the user has never sent a heartbeat (e.g., legacy accounts).
   */
  last_seen: string | null;
  last_activity: string | null;
  created_at: string;
}

export interface LoginCredentials {
  username: string;
  password: string;
}

export interface RegisterData {
  username: string;
  email: string;
  password: string;
  password_confirm: string;
  first_name?: string;
  last_name?: string;
}

export interface LoginResponse {
  access: string;
  refresh: string;
  user: User;
}

export interface RegisterResponse {
  id: number;
  username: string;
  email: string;
  first_name: string;
  last_name: string;
  message: string;
}

// Auth service functions
export const authService = {
  /**
   * Register a new user
   * 
   * REPLACES: Mock registration in AuthPage.tsx
   * 
   * @example
   * const result = await authService.register({
   *   username: 'john_doe',
   *   email: 'john@example.com',
   *   password: 'SecurePass123!',
   *   password_confirm: 'SecurePass123!'
   * });
   */
  async register(data: RegisterData): Promise<RegisterResponse> {
    try {
      const response = await api.post<RegisterResponse>('/auth/register/', data);
      return response.data;
    } catch (error) {
      throw handleApiError(error as any);
    }
  },

  /**
   * Login user and store tokens
   * 
   * REPLACES: Mock login in AuthPage.tsx
   * 
   * @example
   * const { user } = await authService.login({
   *   username: 'john_doe',
   *   password: 'SecurePass123!'
   * });
   */
  async login(credentials: LoginCredentials): Promise<LoginResponse> {
    try {
      const response = await api.post<LoginResponse>('/auth/login/', credentials);
      const { access, refresh, user } = response.data;
      
      // Store tokens
      setTokens(access, refresh);
      
      return response.data;
    } catch (error) {
      throw handleApiError(error as any);
    }
  },

  /**
   * Logout user and clear tokens
   * 
   * REPLACES: Local logout logic
   */
  async logout(): Promise<void> {
    try {
      const refresh = localStorage.getItem('refresh_token');
      if (refresh) {
        await api.post('/auth/logout/', { refresh });
      }
    } catch (error) {
      // Ignore logout errors
    } finally {
      clearTokens();
    }
  },

  /**
   * Get current user profile
   * 
   * REPLACES: Mock user state
   */
  async getProfile(): Promise<User> {
    try {
      const response = await api.get<User>('/auth/profile/');
      return response.data;
    } catch (error) {
      throw handleApiError(error as any);
    }
  },

  /**
   * Update user profile
   */
  async updateProfile(data: Partial<User>): Promise<User> {
    try {
      const response = await api.put<User>('/auth/profile/', data);
      return response.data;
    } catch (error) {
      throw handleApiError(error as any);
    }
  },

  /**
   * Change password
   */
  async changePassword(oldPassword: string, newPassword: string, confirmPassword: string): Promise<void> {
    try {
      await api.post('/auth/password/change/', {
        old_password: oldPassword,
        new_password: newPassword,
        new_password_confirm: confirmPassword,
      });
    } catch (error) {
      throw handleApiError(error as any);
    }
  },

  /**
   * Check if user is authenticated (has valid token)
   */
  isAuthenticated(): boolean {
    return !!localStorage.getItem('access_token');
  },
};

export default authService;
