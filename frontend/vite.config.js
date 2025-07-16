import path from 'path'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'
import { defineConfig } from 'vite'
import { VitePWA } from 'vite-plugin-pwa'


// https://vite.dev/config/
export default defineConfig({
  server: {
    host: true,
    port: 3000,
    allowedHosts: ['localhost', '127.0.0.1', 'frontend'],
  },
  plugins: [
    react(),
    tailwindcss(),
    VitePWA({
      strategies: 'injectManifest',
      injectManifest: {
        swSrc: 'public/sw.js',
        swDest: 'sw.js',
      },
      manifest: {
        name: 'DreamN',
        short_name: 'DreamN',
        start_url: '/',
        scope: '/',
        display: 'standalone',
        background_color: '#fcfcfc',
        theme_color: '#fcfcfc',
        gcm_sender_id: "103953800507",
        icons: [
          {
            "src": "logo-192.png",
            "sizes": "192x192",
            "type": "image/png"
          },
          {
            "src": "logo-512.png",
            "sizes": "512x512",
            "type": "image/png"
          }
        ],
      },
    }),
  ],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
})