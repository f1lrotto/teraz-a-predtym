// Tile cache in front of the slow WMS servers (MŽP geocloud and the city map servers).
// GET /t/{layerId}/{z}/{x}/{y} → the layer's WMS GetMap for that 512 px tile, cached at the edge.
// Only layers marked "proxy": true in catalog/layers.json are served; Esri tiles are never cached here.
import { catalog, layerById, tileBbox, wmsUrl } from '../../catalog/tiles.js';

const DAY = 86400;
const MAX_PARALLEL_PER_HOST = 4;

// Per-isolate limit on parallel upstream requests to one server.
const slots = new Map();
async function limited(host, fn) {
  let s = slots.get(host);
  if (!s) slots.set(host, (s = { active: 0, queue: [] }));
  if (s.active >= MAX_PARALLEL_PER_HOST) await new Promise((resolve) => s.queue.push(resolve));
  s.active++;
  try {
    return await fn();
  } finally {
    s.active--;
    s.queue.shift()?.();
  }
}

const cors = { 'Access-Control-Allow-Origin': '*' };

function cacheSeconds(layer) {
  return layer.group === 'national' && layer.year < 2000 ? 30 * DAY : 7 * DAY;
}

export default {
  async fetch(request, env, ctx) {
    const url = new URL(request.url);
    if (request.method === 'OPTIONS') return new Response(null, { headers: { ...cors, 'Access-Control-Allow-Methods': 'GET' } });
    if (url.pathname === '/health') return new Response('ok', { headers: cors });

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
    const upstream = await limited(new URL(layer.url).host, () =>
      fetch(upstreamUrl, { headers: { 'User-Agent': 'kedysi-a-dnes tile cache' } }),
    );
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
