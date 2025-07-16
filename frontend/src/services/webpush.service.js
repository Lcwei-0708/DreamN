import apiService from './api.service';
import { API } from '@/config/api.config';

export const webpushService = {
  // Subscribe to WebPush
  subscribe: (subscriptionData) => {
    return apiService.post(API.WEBPUSH.SUBSCRIBE, subscriptionData);
  },

  // Unsubscribe from WebPush
  unsubscribe: (endpoint) => {
    return apiService.post(API.WEBPUSH.UNSUBSCRIBE, { endpoint });
  },

  // Get all subscriptions
  getSubscriptions: () => {
    return apiService.get(API.WEBPUSH.SUBSCRIPTIONS);
  },
};

export default webpushService; 