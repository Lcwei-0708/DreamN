import { useState, useEffect, useRef, useCallback } from 'react';
import { useKeycloak } from '@/contexts/keycloakContext';
import ENV from '@/config/env.config';
import { debugLog } from '@/lib/utils';
import { toast } from 'sonner';

/**
 * WebSocket Hook - Manage WebSocket connection state and operations
 */
export const useWebSocket = (url = null, options = {}) => {
  const { getToken, authenticated } = useKeycloak();
  
  // State management
  const [socket, setSocket] = useState(null);
  const [connected, setConnected] = useState(false);
  const [connecting, setConnecting] = useState(false);
  const [error, setError] = useState(null);
  const [lastMessage, setLastMessage] = useState(null);
  const [messageHistory, setMessageHistory] = useState([]);
  
  // Reference management
  const socketRef = useRef(null);
  const reconnectTimeoutRef = useRef(null);
  const reconnectAttemptsRef = useRef(0);
  const messageQueueRef = useRef([]);
  const eventListenersRef = useRef(new Map());
  const isConnectingRef = useRef(false);

  // Config options
  const config = {
    url: url || ENV.WEBSOCKET.URL,
    reconnectInterval: options.reconnectInterval || ENV.WEBSOCKET.RECONNECT_INTERVAL,
    maxReconnectAttempts: options.maxReconnectAttempts || ENV.WEBSOCKET.MAX_RECONNECT_ATTEMPTS,
    enableReconnect: options.enableReconnect !== false,
    enableMessageHistory: options.enableMessageHistory !== false,
    enableAuth: options.enableAuth !== false,
    protocols: options.protocols || [],
    authMethod: options.authMethod || 'url',
    ...options
  };

  // Add event listener (support multiple handlers per type)
  const addEventListener = useCallback((eventType, listener) => {
    if (!eventListenersRef.current.has(eventType)) {
      eventListenersRef.current.set(eventType, []);
    }
    eventListenersRef.current.get(eventType).push(listener);

    return () => {
      const listeners = eventListenersRef.current.get(eventType);
      if (listeners) {
        const index = listeners.indexOf(listener);
        if (index > -1) {
          listeners.splice(index, 1);
        }
        if (listeners.length === 0) {
          eventListenersRef.current.delete(eventType);
        }
      }
    };
  }, []);

  // Send message
  const send = useCallback((msg) => {
    if (socketRef.current && socketRef.current.readyState === WebSocket.OPEN) {
      socketRef.current.send(typeof msg === 'string' ? msg : JSON.stringify(msg));
    }
  }, []);

  // Establish WebSocket connection
  const connect = useCallback(async () => {
    if (socketRef.current?.readyState === WebSocket.OPEN || 
        isConnectingRef.current || 
        connecting) {
      debugLog('WebSocket is already connected or connecting, skipping duplicate connection');
      return;
    }

    if (!config.url) {
      debugLog('WebSocket URL is not set');
      return;
    }

    if (config.enableAuth && !authenticated) {
      debugLog('Authentication required but user is not authenticated');
      return;
    }

    try {
      isConnectingRef.current = true;
      setConnecting(true);
      setError(null);

      let wsUrl = config.url;
      let protocols = [...config.protocols];
      
      // Only pass token as URL param if authMethod is 'url'
      if (config.enableAuth && authenticated && config.authMethod === 'url') {
        const token = getToken();
        if (token) {
          const cleanToken = token.startsWith('Bearer ') ? token.substring(7) : token;
          const separator = wsUrl.includes('?') ? '&' : '?';
          wsUrl = `${wsUrl}${separator}token=${encodeURIComponent(cleanToken)}`;
        }
      }

      debugLog('Initializing WebSocket connection:', wsUrl);

      const newSocket = new WebSocket(wsUrl, protocols.length > 0 ? protocols : undefined);
      socketRef.current = newSocket;

      newSocket.onopen = (event) => {
        debugLog('WebSocket connected');
        if (ENV.DEBUG) {
          toast.success('WebSocket connected');
        }
        
        setSocket(newSocket);
        setConnected(true);
        setConnecting(false);
        isConnectingRef.current = false;
        setError(null);
        reconnectAttemptsRef.current = 0;

        // Send queued messages
        while (messageQueueRef.current.length > 0) {
          const queuedMessage = messageQueueRef.current.shift();
          newSocket.send(queuedMessage);
        }

        // Send auth message after connection if authMethod is 'message'
        if (config.enableAuth && authenticated && config.authMethod === 'message') {
          const token = getToken();
          if (token) {
            const cleanToken = token.startsWith('Bearer ') ? token.substring(7) : token;
            const authMessage = JSON.stringify({
              type: 'auth',
              token: cleanToken
            });
            newSocket.send(authMessage);
          }
        }

        if (config.onOpen) {
          config.onOpen(event);
        }
      };

      newSocket.onmessage = (event) => {
        const message = {
          data: event.data,
          timestamp: new Date(),
          type: 'received'
        };

        setLastMessage(message);
        
        if (config.enableMessageHistory) {
          setMessageHistory(prev => [...prev, message]);
        }

        debugLog('Received WebSocket message:', message);

        if (config.onMessage) {
          config.onMessage(event);
        }

        let parsed;
        try {
          parsed = JSON.parse(event.data);
        } catch {
          parsed = { type: 'raw', data: event.data };
        }

        // Receive and respond to heartbeat message
        if (parsed.type === 'ping') {
          send({ type: 'pong', time: new Date().toISOString() });
        }

        // Call all handlers by type
        const listeners = eventListenersRef.current.get(parsed.type);
        if (listeners && listeners.length > 0) {
          listeners.forEach((handler) => handler(parsed));
        }
      };

      newSocket.onerror = (event) => {
        console.error('WebSocket error:', event);
        setError('WebSocket connection error');
        setConnecting(false);
        isConnectingRef.current = false;
        
        if (config.onError) {
          config.onError(event);
        }
      };

      newSocket.onclose = (event) => {
        debugLog('WebSocket connection closed:', event.code, event.reason);
        setSocket(null);
        setConnected(false);
        setConnecting(false);
        isConnectingRef.current = false;
        
        if (config.onClose) {
          config.onClose(event);
        }

        // Ensure only one reconnect timer
        if (reconnectTimeoutRef.current) {
          clearTimeout(reconnectTimeoutRef.current);
          reconnectTimeoutRef.current = null;
        }

        if (
          config.enableReconnect &&
          reconnectAttemptsRef.current < config.maxReconnectAttempts &&
          !event.wasClean
        ) {
          reconnectAttemptsRef.current += 1;
          const delay = config.reconnectInterval; // Fixed reconnect interval
          debugLog(`WebSocket will reconnect in ${delay}ms (attempt ${reconnectAttemptsRef.current})`);

          reconnectTimeoutRef.current = setTimeout(() => {
            connect();
          }, delay);
        } else if (reconnectAttemptsRef.current >= config.maxReconnectAttempts) {
          setError(`WebSocket reconnect failed, reached max attempts (${config.maxReconnectAttempts})`);
        }
      };

    } catch (err) {
      console.error('Failed to establish WebSocket connection:', err);
      setError(`Failed to connect: ${err.message}`);
      setConnecting(false);
      isConnectingRef.current = false;
    }
  }, [config, authenticated, getToken, send]);

  // Disconnect
  const disconnect = useCallback(() => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = null;
    }

    if (socketRef.current) {
      socketRef.current.close(1000, 'User initiated disconnect');
      socketRef.current = null;
    }

    setSocket(null);
    setConnected(false);
    setConnecting(false);
    isConnectingRef.current = false;
    reconnectAttemptsRef.current = 0;
    messageQueueRef.current = [];
  }, []);

  // Send message (with queue)
  const sendMessage = useCallback((message) => {
    const messageData = typeof message === 'string' ? message : JSON.stringify(message);

    if (socketRef.current?.readyState === WebSocket.OPEN) {
      socketRef.current.send(messageData);
      
      if (config.enableMessageHistory) {
        const messageRecord = {
          data: messageData,
          timestamp: new Date(),
          type: 'sent'
        };
        setMessageHistory(prev => [...prev, messageRecord]);
      }
      
      debugLog('Sent WebSocket message:', messageData);
    } else {
      messageQueueRef.current.push(messageData);
      debugLog('WebSocket not connected, message queued:', messageData);
      
      if (!connecting && !connected) {
        connect();
      }
    }
  }, [connected, connecting, connect, config.enableMessageHistory]);

  // Remove event listener
  const removeEventListener = useCallback((eventType, listener) => {
    const listeners = eventListenersRef.current.get(eventType);
    if (listeners) {
      const index = listeners.indexOf(listener);
      if (index > -1) {
        listeners.splice(index, 1);
      }
      if (listeners.length === 0) {
        eventListenersRef.current.delete(eventType);
      }
    }
  }, []);

  // Clear message history
  const clearMessageHistory = useCallback(() => {
    setMessageHistory([]);
  }, []);

  // Reconnect
  const reconnect = useCallback(() => {
    disconnect();
    setTimeout(connect, 100);
  }, [disconnect, connect]);

  // Get ready state
  const getReadyState = useCallback(() => {
    return socketRef.current?.readyState || WebSocket.CLOSED;
  }, []);

  // Auto connect effect
  useEffect(() => {
    let timeoutId = null;
    
    if (authenticated && config.url) {
      timeoutId = setTimeout(() => {
        connect();
      }, 100);
    }

    return () => {
      if (timeoutId) {
        clearTimeout(timeoutId);
      }
      disconnect();
    };
  }, [authenticated, config.url]);

  // Cleanup effect
  useEffect(() => {
    return () => {
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }
      if (socketRef.current) {
        socketRef.current.close();
      }
    };
  }, []);

  return {
    // State
    socket,
    connected,
    connecting,
    error,
    lastMessage,
    messageHistory,
    
    // Methods
    connect,
    disconnect,
    reconnect,
    sendMessage,
    addEventListener,
    removeEventListener,
    clearMessageHistory,
    getReadyState,
    
    config,
    reconnectAttempts: reconnectAttemptsRef.current,
  };
};

export default useWebSocket;