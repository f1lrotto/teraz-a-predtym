// Real capture date of Esri imagery at a point, from the World Imagery metadata service.
// Metadata layers 0–13 hold footprints for 1.9 cm … 150 m pixels; zoom z needs about layer 23 − z.
export async function captureDate(metadataUrl, lng, lat, zoom, signal) {
  const start = Math.max(0, Math.min(13, 23 - Math.round(zoom)));
  for (let id = start; id <= Math.min(13, start + 3); id++) {
    const params = new URLSearchParams({
      f: 'json',
      where: '1=1',
      outFields: 'SRC_DATE2,NICE_DESC',
      geometry: `${lng},${lat}`,
      inSR: '4326',
      geometryType: 'esriGeometryPoint',
      spatialRel: 'esriSpatialRelIntersects',
      returnGeometry: 'false',
    });
    const res = await fetch(`${metadataUrl}/${id}/query?${params}`, { signal });
    const attrs = (await res.json()).features?.[0]?.attributes;
    if (attrs?.SRC_DATE2) {
      const d = new Date(attrs.SRC_DATE2);
      return `snímka z ${d.getUTCMonth() + 1}/${d.getUTCFullYear()}${attrs.NICE_DESC ? ` · ${attrs.NICE_DESC}` : ''}`;
    }
  }
  return '';
}
