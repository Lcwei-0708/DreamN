import { StrictMode } from 'react'
import './index.css'
import i18n from './i18n'
import AppRouter from './router/AppRouter'
import { createRoot } from 'react-dom/client'
import { I18nextProvider } from 'react-i18next'
import { BrowserRouter } from 'react-router-dom'
import { ThemeProvider } from './contexts/themeContext'
import { KeycloakProvider } from './contexts/keycloakContext'
import { WebSocketProvider } from './contexts/websocketContext'
import { WebpushProvider } from './contexts/webpushContext'

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <ThemeProvider>
      <I18nextProvider i18n={i18n}>
        <KeycloakProvider>
          <WebSocketProvider>
            <WebpushProvider>
              <BrowserRouter>
                <AppRouter />
              </BrowserRouter>
            </WebpushProvider>
          </WebSocketProvider>
        </KeycloakProvider>
      </I18nextProvider>
    </ThemeProvider>
  </StrictMode>
)