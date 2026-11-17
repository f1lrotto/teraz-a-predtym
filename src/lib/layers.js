import { catalog, wmsUrl, WMS_TILE_SIZE } from '../../catalog/tiles.js';

const ESRI_KEY = import.meta.env.VITE_ESRI_KEY || '';

// Layers the site shows: not switched off, not marked broken by the weekly check, city extras only when enabled.
export const layers = catalog.layers.filter(
  (l) => !l.disabled && !l.broken && (l.group === 'national' || catalog.cityExtras),
);
export const national = layers.filter((l) => l.group === 'national');
export const groupNames = catalog.groups;

export function byId(id) {
  return layers.find((l) => l.id === id);
}

export function inBounds(layer, lng, lat) {
  const [w, s, e, n] = layer.bounds;
  return lng >= w && lng <= e && lat >= s && lat <= n;
}

// The MapLibre raster source for one layer.
export function sourceFor(layer) {
  const common = { type: 'raster', maxzoom: layer.maxzoom, bounds: layer.bounds };
  if (layer.kind === 'wms') {
    // Proxied layers go through the same-origin tile cache (worker/src/index.js); the rest hit the WMS directly.
    const tiles = [layer.proxy ? `${location.origin}/t/${layer.id}/{z}/{x}/{y}` : wmsUrl(layer, '{bbox-epsg-3857}')];
    return { ...common, tiles, tileSize: WMS_TILE_SIZE };
  }
  const url = ESRI_KEY && layer.keyedUrl ? layer.keyedUrl.replace('{key}', ESRI_KEY) : layer.url;
  return { ...common, tiles: [url], tileSize: layer.tileSize || 256 };
}

// What the era picker offers at a point: every nationwide era (greyed out when outside its coverage)
// and the city sections whose layers cover the point.
export function erasAt(lng, lat) {
  const cities = [];
  for (const l of layers) {
    if (l.group === 'national' || !inBounds(l, lng, lat)) continue;
    let c = cities.find((c) => c.group === l.group);
    if (!c) cities.push((c = { group: l.group, name: groupNames[l.group], layers: [] }));
    c.layers.push(l);
  }
  for (const c of cities) c.layers.sort((a, b) => a.year - b.year);
  return {
    national: national.map((layer) => ({ layer, here: inBounds(layer, lng, lat) })),
    cities,
  };
}

// "euOnly" layers come from servers that block visitors outside Europe, so the site offers them in the EU only.
// `eu` is null until /geo answers (or when it fails), and then the layer stays offered.
export function available(layer, eu) {
  return !layer.euOnly || eu !== false;
}

// The nationwide era closest in time that this visitor can load, used when the view leaves a city
// or an EU-only era is unavailable.
export function nearestNational(year, eu) {
  return national
    .filter((l) => available(l, eu))
    .reduce((best, l) => (Math.abs(l.year - year) < Math.abs(best.year - year) ? l : best));
}
