// URL hash: #zoom/lat/lng/leftEra/rightEra
const STORE = 'kad:view';

export function readView(fallback) {
  const parts = location.hash.slice(1).split('/');
  if (parts.length >= 3 && parts.slice(0, 3).every((p) => p !== '' && !isNaN(+p))) {
    return { zoom: +parts[0], lat: +parts[1], lng: +parts[2], left: parts[3], right: parts[4] };
  }
  try {
    return { ...fallback, ...JSON.parse(localStorage.getItem(STORE)) };
  } catch {
    return fallback;
  }
}

export function writeView(v) {
  const hash = `#${v.zoom.toFixed(2).replace(/\.?0+$/, '')}/${v.lat.toFixed(5)}/${v.lng.toFixed(5)}/${v.left}/${v.right}`;
  if (location.hash !== hash) history.replaceState(null, '', hash);
  localStorage.setItem(STORE, JSON.stringify(v));
}
