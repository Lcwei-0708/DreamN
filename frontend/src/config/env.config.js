// Centralized management of all environment variables for frontend (Vite/React only).
// Add new variables here.

// Vite
export  const ENV = {
    DEBUG: process.env.NODE_ENV === 'development' || false,
    API: {
      BASE_URL: import.meta.env.VITE_API_BASE_URL,
    },
    KEYCLOAK: {
      SERVER_URL: import.meta.env.VITE_KEYCLOAK_SERVER_URL,
      REALM: import.meta.env.VITE_KEYCLOAK_REALM,
      CLIENT: import.meta.env.VITE_KEYCLOAK_CLIENT,
      SUPER_ROLE: import.meta.env.VITE_KEYCLOAK_SUPER_ROLE || 'tsadmin',
    },
    WEBSOCKET: {
      URL: import.meta.env.VITE_WEBSOCKET_URL,
      RECONNECT_INTERVAL: parseInt(import.meta.env.VITE_WEBSOCKET_RECONNECT_INTERVAL) || 3000,
      MAX_RECONNECT_ATTEMPTS: parseInt(import.meta.env.VITE_WEBSOCKET_MAX_RECONNECT_ATTEMPTS) || 5,
    },
    VAPID: {
      PUBLIC_KEY: import.meta.env.VITE_VAPID_PUBLIC_KEY,
    },
  };

export default ENV;