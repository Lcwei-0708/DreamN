import axios from 'axios';
import { ENV } from '@/config/env.config';
import { handleApiError, setErrorHandler } from './error.service';

// Create axios instance
const apiClient = axios.create({
  baseURL: ENV.API.BASE_URL,
  timeout: 15000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Global token getter functions (set by KeycloakProvider)
let getTokenFunction = null;
let logoutFunction = null;

// Set token getter functions
export const setTokenGetter = (getToken, logout) => {
  getTokenFunction = getToken;
  logoutFunction = logout;
};

// Export error handler setter for convenience
export { setErrorHandler };

// Request interceptor - automatically get latest token for each request
apiClient.interceptors.request.use(
  async (config) => {
    if (!getTokenFunction) {
      console.error('Token getter function not set');
      return config;
    }

    try {
      const latestToken = getTokenFunction();
      
      if (latestToken) {
        config.headers.Authorization = `Bearer ${latestToken}`;
      } else {
        delete config.headers.Authorization;
      }
    } catch (error) {
      console.error('Error getting token:', error);
      delete config.headers.Authorization;
    }
    
    return config;
  },
  (error) => {
    console.error('Request interceptor error:', error);
    return Promise.reject(error);
  }
);

// Response interceptor
apiClient.interceptors.response.use(
  (response) => {
    // If backend returns { data } format, return data directly
    if (response.data && response.data.data !== undefined) {
      return response.data.data;
    }
    return response.data;
  },
  (error) => {
    // Use centralized error handler
    handleApiError(error, logoutFunction);
    return Promise.reject(error);
  }
);

// API service
export const apiService = {
  get: (url, params = {}) => {
    return apiClient.get(url, { params });
  },

  post: (url, data = {}) => {
    return apiClient.post(url, data);
  },

  put: (url, data = {}) => {
    return apiClient.put(url, data);
  },

  delete: (url) => {
    return apiClient.delete(url);
  },

  upload: (url, formData) => {
    return apiClient.post(url, formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
  },
};

export default apiService;