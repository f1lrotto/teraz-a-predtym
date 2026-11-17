// Shared by the frontend and the tile-cache Worker.
import catalog from './layers.json' with { type: 'json' };

export { catalog };

export const WMS_TILE_SIZE = 512;

const R = 20037508.342789244;

// Web Mercator bbox of XYZ tile z/x/y.
export function tileBbox(z, x, y) {
  const size = (2 * R) / 2 ** z;
  return [-R + x * size, R - (y + 1) * size, -R + (x + 1) * size, R - y * size];
}

// GetMap URL for a WMS layer. `bbox` is an array or MapLibre's `{bbox-epsg-3857}` placeholder.
export function wmsUrl(layer, bbox, size = WMS_TILE_SIZE) {
  const params = new URLSearchParams({
    SERVICE: 'WMS',
    VERSION: '1.3.0',
    REQUEST: 'GetMap',
    LAYERS: layer.layers,
    STYLES: '',
    CRS: 'EPSG:3857',
    WIDTH: String(size),
    HEIGHT: String(size),
    FORMAT: layer.format,
    TRANSPARENT: 'true',
  });
  const box = Array.isArray(bbox) ? bbox.map((v) => v.toFixed(2)).join(',') : bbox;
  return `${layer.url}?${params}&BBOX=${box}`;
}

export function layerById(id) {
  return catalog.layers.find((l) => l.id === id);
}
