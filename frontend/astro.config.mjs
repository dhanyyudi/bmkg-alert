import { defineConfig } from 'astro/config';
import react from '@astrojs/react';
import tailwind from '@astrojs/tailwind';
import node from '@astrojs/node';

// https://astro.build/config
export default defineConfig({
  output: 'server',
  adapter: node({
    mode: 'standalone'
  }),
  integrations: [react(), tailwind()],
  server: {
    host: '0.0.0.0',
    port: 3000,
  },
    vite: {
        optimizeDeps: {
            include: ['maplibre-gl', 'react-map-gl/maplibre'],
            esbuildOptions: {
                target: 'esnext',
            },
        },
        build: {
            target: 'esnext',
        },
        server: {
            proxy: {
                '/api': {
                    target: 'http://localhost:8000',
                    changeOrigin: true,
                }
            }
        }
    }
});
