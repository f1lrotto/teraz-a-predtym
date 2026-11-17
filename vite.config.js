import { defineConfig } from 'vite';
import { svelte } from '@sveltejs/vite-plugin-svelte';

export default defineConfig({
  plugins: [svelte()],
  server: {
    host: true,
    allowedHosts: true,
    // Tile, geo and analytics requests go to the local Worker from `npm run dev:tiles`.
    proxy: { '/t/': 'http://localhost:8787', '/geo': 'http://localhost:8787', '/k/': 'http://localhost:8787' },
  },
  preview: { host: true, allowedHosts: true },
});
