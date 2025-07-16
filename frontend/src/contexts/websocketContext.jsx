import ENV from '@/config/env.config';
import { useWebSocket } from '@/hooks/useWebsocket';
import { useKeycloak } from '@/contexts/keycloakContext';
import React, { createContext, useContext, useEffect } from 'react';

const WebSocketContext = createContext(null);

/**
 * WebSocket Provider Component
 * Provides global WebSocket connection management
 */
export const WebSocketProvider = ({ 
  children, 
  url = ENV.WEBSOCKET.URL,
  options = {} 
}) => {
  const { authenticated } = useKeycloak();
  
  const defaultOptions = {
    enableAuth: true,
    enableReconnect: true,
    enableMessageHistory: true,
    maxReconnectAttempts: 5,
    reconnectInterval: 3000,
    ...options
  };

  const webSocketData = useWebSocket(url, defaultOptions);

  // Global error handling
  useEffect(() => {
    if (webSocketData.error) {
      console.error('WebSocket global error:', webSocketData.error);
      // You can add global error handling logic here, such as showing notifications
    }
  }, [webSocketData.error]);

  return (
    <WebSocketContext.Provider value={webSocketData}>
      {children}
    </WebSocketContext.Provider>
  );
};

/**
 * Hook to get WebSocket state from Context
 */
export const useWebSocketContext = () => {
  const context = useContext(WebSocketContext);
  
  if (!context) {
    throw new Error('useWebSocketContext must be used within a WebSocketProvider');
  }
  
  return context;
};

/**
 * Higher-order component wrapper to provide WebSocket functionality
 */
export const withWebSocket = (Component) => {
  return function WebSocketWrappedComponent(props) {
    return (
      <WebSocketProvider>
        <Component {...props} />
      </WebSocketProvider>
    );
  };
};

export default WebSocketProvider;