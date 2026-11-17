import { defineConfig } from 'vite';
import { svelte } from '@sveltejs/vite-plugin-svelte';

export default defineConfig({
  plugins: [svelte()],
  // With VITE_TILE_PROXY=/tiles, dev tile requests go through a local `npm run worker:dev`.
  server: {
    host: true,
    allowedHosts: true,
    proxy: { '/tiles': { target: 'http://localhost:8787', rewrite: (p) => p.replace(/^\/tiles/, '') } },
  },
  preview: { host: true, allowedHosts: true },
});
