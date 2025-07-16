import apiService from './api.service';
import { API } from '@/config/api.config';

export const userService = {
  // Get user info
  getInfo: () => {
    return apiService.get(API.USER.INFO);
  },

  // Update user info
  update: (userData) => {
    return apiService.put(API.USER.UPDATE, userData);
  },

  // Change password
  changePassword: (passwordData) => {
    return apiService.post(API.USER.CHANGE_PASSWORD, passwordData);
  },
};

export default userService; 