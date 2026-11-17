// Tile cache in front of the slow WMS servers (MŽP geocloud and the city map servers).
// GET /t/{layerId}/{z}/{x}/{y} → the layer's WMS GetMap for that 512 px tile, cached at the edge.
// Only layers marked "proxy": true in catalog/layers.json are served; Esri and GKÚ orthophoto tiles are never cached here.
import { catalog, layerById, tileBbox, wmsUrl } from '../../catalog/tiles.js';

const DAY = 86400;
const cors = { 'Access-Control-Allow-Origin': '*' };

function cacheSeconds(layer) {
  return layer.group === 'national' && layer.year < 2000 ? 30 * DAY : 7 * DAY;
}

// Same-origin proxy for PostHog's EU cloud (src/lib/analytics.js), so ad blockers do not drop the events.
// /k/static/* and /k/array/* are SDK files and remote config from the asset host; everything else is the API.
async function posthog(request, url, ctx) {
  const path = url.pathname.slice(2) + url.search;
  if (path.startsWith('/static/') || path.startsWith('/array/')) {
    const hit = await caches.default.match(request);
    if (hit) return hit;
    const response = await fetch(`https://eu-assets.i.posthog.com${path}`);
    if (response.ok) ctx.waitUntil(caches.default.put(request, response.clone()));
    return response;
  }
  const headers = new Headers(request.headers);
  headers.delete('cookie');
  // The visitor's IP, for PostHog's country lookup and its cookieless visitor hash.
  headers.set('X-Forwarded-For', request.headers.get('CF-Connecting-IP') || '');
  return fetch(`https://eu.i.posthog.com${path}`, {
    method: request.method,
    headers,
    body: ['GET', 'HEAD'].includes(request.method) ? null : request.body,
  });
}

export default {
  async fetch(request, env, ctx) {
    const url = new URL(request.url);
    if (request.method === 'OPTIONS') return new Response(null, { headers: { ...cors, 'Access-Control-Allow-Methods': 'GET' } });
    if (url.pathname === '/health') return new Response('ok', { headers: cors });
    // Whether the visitor is in the EU, for layers whose server serves only European visitors ("euOnly" in the catalog).
    if (url.pathname === '/geo') {
      return Response.json(
        { eu: request.cf?.isEUCountry === '1', country: request.cf?.country ?? null },
        { headers: { 'Cache-Control': 'private, no-store' } },
      );
    }

    if (url.pathname.startsWith('/k/')) return posthog(request, url, ctx);

    const m = url.pathname.match(/^\/t\/([\w-]+)\/(\d{1,2})\/(\d+)\/(\d+)(?:\.\w+)?$/);
    if (!m || request.method !== 'GET') return new Response('Not found', { status: 404, headers: cors });
    const [, id, zs, xs, ys] = m;
    const [z, x, y] = [+zs, +xs, +ys];
    const layer = layerById(id);
    if (!layer || layer.kind !== 'wms' || !layer.proxy || layer.broken) return new Response('Unknown layer', { status: 404, headers: cors });
    if (layer.group !== 'national' && !catalog.cityExtras) return new Response('Disabled', { status: 404, headers: cors });
    if (z > 20 || x >= 2 ** z || y >= 2 ** z) return new Response('Bad tile', { status: 400, headers: cors });

    const cacheKey = new Request(`${url.origin}/t/${id}/${z}/${x}/${y}`);
    const cache = caches.default;
    const hit = await cache.match(cacheKey);
    if (hit) return hit;

    const upstreamUrl = wmsUrl(layer, tileBbox(z, x, y));
    // No per-server queue here: a Worker request may not wait on a promise that another request resolves
    // (the runtime cancels it as hung), and an isolate-local limit would not bound the total anyway.
    const upstream = await fetch(upstreamUrl, { headers: { 'User-Agent': 'kedysi-a-dnes tile cache' } });
    const type = upstream.headers.get('Content-Type') || '';
    if (!upstream.ok || !type.startsWith('image/')) {
      return new Response(`Upstream ${upstream.status}`, { status: 502, headers: { ...cors, 'Cache-Control': 'no-store' } });
    }

    const maxAge = cacheSeconds(layer);
    const response = new Response(upstream.body, {
      headers: { ...cors, 'Content-Type': type, 'Cache-Control': `public, max-age=${maxAge}, immutable` },
    });
    ctx.waitUntil(cache.put(cacheKey, response.clone()));
    return response;
  },
};
