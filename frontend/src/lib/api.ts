/**
 * API Configuration and Base Service
 * 
 * This file contains the API configuration and axios instance setup.
 * All API calls should use this configured instance.
 * 
 * Backend Integration:
 * - Connects to Django REST Framework backend
 * - Handles JWT authentication
 * - Manages token refresh automatically
 */

import axios, { AxiosError, InternalAxiosRequestConfig } from 'axios';

// Use a relative URL by default to leverage Vite's development proxy.
// Only use the environment's configured API URL in production.
const isDev = import.meta.env.DEV;
const API = isDev ? '' : (import.meta.env.VITE_API_URL || '');
export const BASE_URL = API || window.location.origin;
export const API_BASE_URL = `${API}/api/v1`;

// Export for debugging purposes
export const getApiInfo = () => ({
  baseUrl: API_BASE_URL,
  isLoopback: true,
});

// Create axios instance with default config
const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Token storage keys
const ACCESS_TOKEN_KEY = 'access_token';
const REFRESH_TOKEN_KEY = 'refresh_token';

// Token management functions
export const getAccessToken = (): string | null => {
  return localStorage.getItem(ACCESS_TOKEN_KEY);
};

export const getRefreshToken = (): string | null => {
  return localStorage.getItem(REFRESH_TOKEN_KEY);
};

export const setTokens = (access: string, refresh: string): void => {
  localStorage.setItem(ACCESS_TOKEN_KEY, access);
  localStorage.setItem(REFRESH_TOKEN_KEY, refresh);
};

export const clearTokens = (): void => {
  localStorage.removeItem(ACCESS_TOKEN_KEY);
  localStorage.removeItem(REFRESH_TOKEN_KEY);
};

// Request interceptor - add auth token to requests
api.interceptors.request.use(
  (config: InternalAxiosRequestConfig) => {
    const token = getAccessToken();
    if (token && config.headers) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error: AxiosError) => {
    return Promise.reject(error);
  }
);

// Response interceptor - handle token refresh
api.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    const originalRequest = error.config as InternalAxiosRequestConfig & { _retry?: boolean };

    // If 401 and not already retrying, attempt token refresh
    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true;

      const refreshToken = getRefreshToken();
      if (refreshToken) {
        try {
          const response = await axios.post(`${API_BASE_URL}/auth/token/refresh/`, {
            refresh: refreshToken,
          });

          const { access } = response.data;
          localStorage.setItem(ACCESS_TOKEN_KEY, access);

          // Retry original request with new token
          if (originalRequest.headers) {
            originalRequest.headers.Authorization = `Bearer ${access}`;
          }
          return api(originalRequest);
        } catch (refreshError) {
          // Refresh failed, clear tokens and redirect to login
          clearTokens();
          window.location.href = '/';
          return Promise.reject(refreshError);
        }
      }
    }

    return Promise.reject(error);
  }
);

export default api;

// Error handling helper
export interface ApiError {
  message: string;
  errors?: Record<string, string[]>;
  isNetworkError?: boolean;
}

/**
 * Get a user-friendly error message for network errors.
 * Provides specific guidance for local backend connectivity issues.
 */
const getNetworkErrorMessage = (error: AxiosError): string => {
  // No response means network error (server unreachable)
  if (!error.response) {
    const baseUrl = API_BASE_URL;

    if (error.code === 'ECONNABORTED') {
      return `Request timed out. The server at ${baseUrl} is not responding. Please check if the backend is running.`;
    }

    if (error.code === 'ERR_NETWORK' || error.message === 'Network Error') {
      return `Cannot connect to the server. Please verify:\n` +
        `1. The backend server is running (py manage.py runserver 0.0.0.0:8080)\n` +
        `2. Your Vite proxy/network settings are correct\n` +
        `3. Nothing else is already using the backend port`;
    }

    return `Network error: Unable to reach the server. Please check your connection.`;
  }

  return '';
};

export const handleApiError = (error: AxiosError): ApiError => {
  // Check for network errors first
  const networkErrorMsg = getNetworkErrorMessage(error);
  if (networkErrorMsg) {
    console.error('[API] Network Error:', error.message, '\nURL:', error.config?.url);
    return { message: networkErrorMsg, isNetworkError: true };
  }

  if (error.response?.data) {
    const data = error.response.data as Record<string, unknown>;

    // Handle DRF validation errors
    if (typeof data === 'object') {
      const errors: Record<string, string[]> = {};
      let message = 'An error occurred';

      for (const [key, value] of Object.entries(data)) {
        if (key === 'detail') {
          message = String(value);
        } else if (key === 'message') {
          message = String(value);
        } else if (Array.isArray(value)) {
          errors[key] = value.map(String);
        } else if (typeof value === 'string') {
          errors[key] = [value];
        }
      }

      return { message, errors: Object.keys(errors).length > 0 ? errors : undefined };
    }
  }

  // HTTP status-based messages
  if (error.response?.status) {
    const status = error.response.status;
    if (status === 403) return { message: 'Access denied. You do not have permission for this action.' };
    if (status === 404) return { message: 'The requested resource was not found.' };
    if (status === 500) return { message: 'Server error. Please try again later.' };
    if (status === 502) return { message: 'Bad gateway. The server may be restarting.' };
    if (status === 503) return { message: 'Service unavailable. Please try again later.' };
  }

  return { message: error.message || 'An unexpected error occurred' };
};
