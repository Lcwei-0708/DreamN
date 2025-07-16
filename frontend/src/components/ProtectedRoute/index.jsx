import React from "react";
import ErrorPage from "@/pages/Error";
import Loading from "@/components/ui/loading";
import { debugLog } from "@/lib/utils";
import { useTranslation } from "react-i18next";
import { useEffect, useCallback, useMemo } from "react";
import { useKeycloak } from "@/contexts/keycloakContext";

export default function ProtectedRoute({ permissionKey, children }) {
  const { t } = useTranslation();
  const { 
    loading, 
    authenticated, 
    login,
    hasModulePermission, 
    isInitialized,
    isInitializing,
    initializationFailed,
    error,
    isTokenExpired,
    updateToken
  } = useKeycloak();

  // Memoized permission check to avoid unnecessary recalculations
  const hasPermission = useMemo(() => {
    if (!permissionKey) return true;
    if (!authenticated) return false;
    return hasModulePermission(permissionKey);
  }, [permissionKey, authenticated, hasModulePermission]);

  // Handle login redirect
  const handleLogin = useCallback(async () => {
    if (login && !authenticated) {
      try {
        debugLog('Redirecting to login...');
        await login();
      } catch (error) {
        console.error('Login redirect failed:', error);
      }
    }
  }, [login, authenticated]);

  // Handle token refresh if needed
  const handleTokenRefresh = useCallback(async () => {
    if (authenticated && isTokenExpired && isTokenExpired(30) && updateToken) {
      try {
        debugLog('Token is expiring soon, refreshing...');
        await updateToken(30);
      } catch (error) {
        console.error('Token refresh failed:', error);
        // Token refresh failed, redirect to login
        handleLogin();
      }
    }
  }, [authenticated, isTokenExpired, updateToken, handleLogin]);

  // Effect to handle authentication state changes
  useEffect(() => {
    // Don't do anything if still initializing
    if (isInitializing || loading) {
      return;
    }

    // If initialization failed, show error
    if (initializationFailed) {
      return;
    }

    // If initialized but not authenticated, redirect to login
    // But only if this route requires authentication (has permissionKey or is protected)
    if (isInitialized && !authenticated && (permissionKey || true)) {
      // Add small delay to avoid immediate redirect after page load
      const timer = setTimeout(() => {
        handleLogin();
      }, 100);
      
      return () => clearTimeout(timer);
    }

    // If authenticated, check token validity
    if (authenticated) {
      handleTokenRefresh();
    }
  }, [
    isInitializing,
    loading,
    initializationFailed,
    isInitialized,
    authenticated,
    permissionKey,
    handleLogin,
    handleTokenRefresh
  ]);

  // Show loading during initialization
  if (isInitializing || loading) {
    return <Loading fullScreen />;
  }

  // Show error if initialization failed
  if (initializationFailed) {
    return (
      <>
        {React.cloneElement(children, {
          children: (
            <ErrorPage 
              code={500} 
              message={error}
              showRetry={true}
              onRetry={() => window.location.reload()}
            />
          )
        })}
      </>
    );
  }

  // Show loading if not authenticated (will redirect to login)
  if (!authenticated) {
    return <Loading fullScreen />;
  }

  // Check token validity - show loading while refreshing
  if (isTokenExpired && isTokenExpired(30)) {
    return <Loading fullScreen />;
  }

  // Check permissions if required
  if (permissionKey && !hasPermission) {
    return (
      <>
        {React.cloneElement(children, {
          children: (
            <ErrorPage 
              code={403} 
              message={t("errors.403.message")}
            />
          )
        })}
      </>
    );
  }

  // All checks passed, render children
  return <>{children}</>;
}
