import React, { createContext, useContext, useMemo } from 'react';
import { useWebpush } from '@/hooks/useWebpush';

const WebpushContext = createContext(null);

export function WebpushProvider({ children }) {
  const webpush = useWebpush();
  const value = useMemo(() => webpush, [webpush]);
  return (
    <WebpushContext.Provider value={value}>
      {children}
    </WebpushContext.Provider>
  );
}

export function useWebpushContext() {
  return useContext(WebpushContext);
}