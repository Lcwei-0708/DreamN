import ENV from '@/config/env.config';
import { toast } from "sonner";
import { debugLog } from '@/lib/utils';
import { useState, useCallback, useEffect, useRef } from 'react';
import { webpushService } from '@/services/webpush.service';
import { useKeycloak } from '@/contexts/keycloakContext';

// Convert base64 to Uint8Array
function urlBase64ToUint8Array(base64String) {
  const padding = "=".repeat((4 - (base64String.length % 4)) % 4);
  const base64 = (base64String + padding).replace(/\-/g, "+").replace(/_/g, "/");
  const rawData = window.atob(base64);
  return Uint8Array.from([...rawData].map((char) => char.charCodeAt(0)));
}

export function useWebpush() {
  const { authenticated, loading: keycloakLoading, getToken } = useKeycloak();
  const [subscription, setSubscription] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [autoSubscribed, setAutoSubscribed] = useState(false);
  const [initialized, setInitialized] = useState(false);
  
  // Use ref to avoid duplicate execution
  const initializingRef = useRef(false);
  const mountedRef = useRef(true);

  // Check browser support
  const checkBrowserSupport = useCallback(() => {    
    if (!('serviceWorker' in navigator)) {
      return { supported: false, message: "This browser does not support Service Worker" };
    }
    
    if (!('PushManager' in window)) {
      return { supported: false, message: "This browser does not support Push Notification" };
    }
    
    if (!('Notification' in window)) {
      return { supported: false, message: "This browser does not support Notification feature" };
    }
    return { supported: true, message: "" };
  }, []);

  // Auto subscribe to Web Push
  const autoSubscribe = useCallback(async () => {
    if (!authenticated || !getToken()) {
      debugLog('User not authenticated, skipping auto subscribe');
      return null;
    }

    // Check if user has already been prompted for this session
    if (autoSubscribed) {
      debugLog('Auto subscription already attempted this session');
      return null;
    }

    try {
      debugLog('Starting auto Web Push subscription...');
      setAutoSubscribed(true);

      // Check notification permission
      let permission = Notification.permission;
      
      if (permission === 'denied') {
        debugLog('Notification permission denied, cannot auto subscribe');
        return null;
      }

      if (permission === 'default') {
        debugLog('Requesting notification permission...');
        permission = await Notification.requestPermission();
        
        if (permission === 'denied') {
          debugLog('User denied notification permission');
          return null;
        }
        
        if (permission !== 'granted') {
          debugLog('Notification permission not granted');
          return null;
        }
      }

      // Register Service Worker
      let serviceWorkerReg = await navigator.serviceWorker.getRegistration();
      if (!serviceWorkerReg) {
        debugLog('Registering Service Worker for auto subscription...');
        await navigator.serviceWorker.register('/sw.js');
        serviceWorkerReg = await navigator.serviceWorker.ready;
      }

      // Create subscription
      const publicKey = ENV.VAPID.PUBLIC_KEY;
      if (!publicKey) {
        throw new Error('VAPID public key not set');
      }

      const sub = await serviceWorkerReg.pushManager.subscribe({
        userVisibleOnly: true,
        applicationServerKey: urlBase64ToUint8Array(publicKey),
      });

      debugLog('Auto subscription created');
      setSubscription(sub);

      // Send subscription to backend
      await webpushService.subscribe({
        endpoint: sub.endpoint,
        keys: sub.toJSON().keys,
        user_agent: navigator.userAgent
      });

      debugLog('Auto Web Push subscription successful');
      toast.success('Web Push notifications enabled!');
      return sub;

    } catch (e) {
      console.warn('Auto Web Push subscription failed:', e);
      // Don't show error toast for auto subscription failures
      return null;
    }
  }, [authenticated, getToken, autoSubscribed]);

  // Sync existing subscription to backend
  const syncExistingSubscription = useCallback(async (existingSubscription) => {
    if (!authenticated || !getToken()) {
      debugLog('Unauthenticated, skipping sync');
      return;
    }

    try {
      debugLog('Found existing subscription, syncing to backend...');
      await webpushService.subscribe({
        endpoint: existingSubscription.endpoint,
        keys: existingSubscription.toJSON().keys,
        user_agent: navigator.userAgent
      });
    } catch (syncError) {
      console.warn('Failed to sync existing subscription to backend:', syncError);
      // If sync fails and is authentication error, may need to clear local subscription
      if (syncError.response?.status === 401) {
        debugLog('Authentication failed, clearing local subscription');
        try {
          await existingSubscription.unsubscribe();
          setSubscription(null);
        } catch (unsubError) {
          console.warn('Failed to clear local subscription:', unsubError);
        }
      }
    }
  }, [authenticated, getToken]);

  // Initialize WebPush
  const initializeWebPush = useCallback(async () => {
    // Avoid duplicate initialization
    if (initializingRef.current || initialized) {
      debugLog('WebPush is initializing or already initialized, skipping');
      return;
    }

    // Check authentication status
    if (!authenticated || keycloakLoading) {
      debugLog('Waiting for Keycloak authentication to complete...');
      return;
    }

    // Check if there is a token
    if (!getToken()) {
      debugLog('No valid token, cannot initialize WebPush');
      return;
    }

    // Check browser support
    const browserCheck = checkBrowserSupport();
    if (!browserCheck.supported) {
      debugLog('Browser does not support WebPush:', browserCheck.message);
      setError(new Error(browserCheck.message));
      return;
    }

    initializingRef.current = true;
    setLoading(true);

    try {
      debugLog('Initializing WebPush...');
      
      let serviceWorkerReg = await navigator.serviceWorker.getRegistration();

      // Register Service Worker (if not registered)
      if (!serviceWorkerReg) {
        debugLog('Registering Service Worker...');
        await navigator.serviceWorker.register('/sw.js');
        serviceWorkerReg = await navigator.serviceWorker.ready;
      }

      // Check existing subscription
      const existingSubscription = await serviceWorkerReg.pushManager.getSubscription();
      
      if (existingSubscription) {
        setSubscription(existingSubscription);
        await syncExistingSubscription(existingSubscription);
        debugLog('Existing subscription synced');
      } else {
        debugLog('No existing subscription, attempting auto subscription...');
        // 自動註冊 Web Push
        await autoSubscribe();
      }

      if (mountedRef.current) {
        setInitialized(true);
        debugLog('WebPush initialized');
      }

    } catch (e) {
      console.error('Failed to initialize WebPush:', e);
      if (mountedRef.current) {
        setError(e);
      }
    } finally {
      initializingRef.current = false;
      if (mountedRef.current) {
        setLoading(false);
      }
    }
  }, [authenticated, keycloakLoading, getToken, checkBrowserSupport, syncExistingSubscription, autoSubscribe, initialized]);

  // Listen for authentication status changes
  useEffect(() => {
    if (authenticated && !keycloakLoading && !initialized) {
      // Use setTimeout to avoid duplicate execution in strict mode
      const timer = setTimeout(() => {
        if (mountedRef.current) {
          initializeWebPush();
        }
      }, 100);

      return () => clearTimeout(timer);
    }
  }, [authenticated, keycloakLoading, initialized, initializeWebPush]);

  // Cleanup function
  useEffect(() => {
    mountedRef.current = true;
    return () => {
      mountedRef.current = false;
    };
  }, []);

  // Manual subscription
  const subscribe = useCallback(async () => {
    if (!authenticated || !getToken()) {
      throw new Error('User not authenticated');
    }

    setLoading(true);
    setError(null);
    try {
      debugLog('Start manual WebPush registration...');
      let reg = await navigator.serviceWorker.getRegistration();
      if (!reg) {
        debugLog('Registering Service Worker...');
        await navigator.serviceWorker.register('/sw.js');
        reg = await navigator.serviceWorker.ready;
      }

      let sub = await reg.pushManager.getSubscription();
      
      if (!sub) {
        // Create new subscription
        if (!('PushManager' in window)) throw new Error('Not support Push API');
        if (Notification.permission === 'denied') throw new Error('Notification permission denied');
        if (Notification.permission === 'default') {
          const permission = await Notification.requestPermission();
          if (permission === 'denied') throw new Error('User denied notification permission');
        }
        const publicKey = ENV.VAPID.PUBLIC_KEY;
        if (!publicKey) throw new Error('VAPID public key not set');
        sub = await reg.pushManager.subscribe({
          userVisibleOnly: true,
          applicationServerKey: urlBase64ToUint8Array(publicKey),
        });
        debugLog('New subscription created');
      } else {
        debugLog('Using existing subscription');
      }
      
      setSubscription(sub);
      
      // Send subscription request to backend
      debugLog('Sending subscription request to backend...');
      await webpushService.subscribe({
        endpoint: sub.endpoint,
        keys: sub.toJSON().keys,
        user_agent: navigator.userAgent
      });
      
      toast.success('Web Push subscription successful!');
      debugLog('Web Push registration complete');
      return sub;
    } catch (e) {
      console.error('Web Push registration failed:', e);
      setError(e);
      throw e;
    } finally {
      setLoading(false);
    }
  }, [authenticated, getToken]);

  // Unsubscribe
  const unsubscribe = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      debugLog('Start to unsubscribe Web Push...');
      const reg = await navigator.serviceWorker.getRegistration();
      if (!reg) throw new Error('Service Worker not found');
      const sub = await reg.pushManager.getSubscription();
      if (sub) {
        debugLog('Sending unsubscribe request to backend...');
        try {
          await webpushService.unsubscribe(sub.endpoint);
        } catch (backendError) {
          console.warn('Backend unsubscribe failed, may not exist:', backendError);
        }
        debugLog('Unsubscribing from browser...');
        await sub.unsubscribe();
        setSubscription(null);
        setAutoSubscribed(false);
        debugLog('Web Push unsubscribe complete');
      } else {
        debugLog('No existing subscription found');
      }
    } catch (e) {
      console.error('Web Push unsubscribe failed:', e);
      setError(e);
      throw e;
    } finally {
      setLoading(false);
    }
  }, []);

  // Get current subscription info
  const getSubscription = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      debugLog('Getting current Web Push subscription info...');
      const reg = await navigator.serviceWorker.getRegistration();
      if (!reg) {
        debugLog('No Service Worker registration found');
        setSubscription(null);
        return null;
      }
      const sub = await reg.pushManager.getSubscription();
      setSubscription(sub);
      debugLog('Current subscription status:', sub ? 'Subscribed' : 'Not subscribed');
      return sub;
    } catch (e) {
      console.error('Failed to get Web Push subscription info:', e);
      setError(e);
      throw e;
    } finally {
      setLoading(false);
    }
  }, []);

  // Request notification permission
  const requestPermission = useCallback(async () => {
    if ("Notification" in window) {
      const result = await Notification.requestPermission();
      debugLog('Permission request result:', result);
      return result;
    }
    return "denied";
  }, []);

  return {
    subscription,
    loading,
    error,
    initialized,
    autoSubscribed,
    subscribe,
    unsubscribe,
    getSubscription,
    checkBrowserSupport,
    requestPermission,
  };
}
