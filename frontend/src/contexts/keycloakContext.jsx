import React, { createContext, useContext } from 'react';
import { setTokenGetter } from '@/services/api.service';
import { useKeycloak as useKeycloakHook } from '@/hooks/useKeycloak';

const KeycloakContext = createContext(null);

/**
 * Keycloak Provider Component
 * Provide Keycloak state to the entire app
 */
export const KeycloakProvider = ({ children }) => {
  const keycloakData = useKeycloakHook();

  // Set token getter function to API service
  React.useEffect(() => {
    if (keycloakData.getToken && keycloakData.logout) {
      setTokenGetter(keycloakData.getToken, keycloakData.logout);
    }
  }, [keycloakData.getToken, keycloakData.logout]);

  return (
    <KeycloakContext.Provider value={keycloakData}>
      {children}
    </KeycloakContext.Provider>
  );
};

/**
 * Hook to get Keycloak state from Context
 */
export const useKeycloak = () => {
  const context = useContext(KeycloakContext);
  
  if (!context) {
    throw new Error('useKeycloak must be used within a KeycloakProvider');
  }
  
  return context;
};

export default KeycloakProvider; 