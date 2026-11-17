// Place suggestions while typing, from Photon (OpenStreetMap data). Nominatim's usage policy forbids
// autocomplete; Photon's public server allows it at a reasonable rate.
const KIND = {
  city: 'mesto', town: 'mesto', village: 'obec', municipality: 'obec', hamlet: 'osada', isolated_dwelling: 'osada',
  suburb: 'mestská časť', borough: 'mestská časť', quarter: 'štvrť', neighbourhood: 'štvrť', locality: 'lokalita',
  district: 'okres', region: 'kraj', cadastral_community: 'katastrálne územie', castle: 'hrad', peak: 'vrch',
  river: 'rieka', canal: 'kanál',
};
const ZOOM = { house: 17, street: 16 };
// Places, streets, landmarks and nature only: shops, stops and post offices named after their town crowd out the town.
const TAGS = [
  'place', 'highway', 'historic', 'tourism', 'natural', 'waterway', ':!bus_stop', ':!platform', ':!motorway_junction', ':!stream',
];

// Up to six places in Slovakia matching `q`, nearer to `near` ({ lng, lat }) ranked higher.
export async function suggest(q, near, signal) {
  const params = new URLSearchParams({
    q, limit: '10', lang: 'default', countrycode: 'SK', lat: near.lat.toFixed(3), lon: near.lng.toFixed(3), zoom: '10',
  });
  for (const tag of TAGS) params.append('osm_tag', tag);
  const res = await fetch(`https://photon.komoot.io/api/?${params}`, { signal });
  if (!res.ok) throw new Error(`Photon ${res.status}`);
  const places = [];
  for (const { properties: p, geometry } of (await res.json()).features) {
    const [lng, lat] = geometry.coordinates;
    const name = p.name || [p.street, p.housenumber].filter(Boolean).join(' ');
    const kind = KIND[p.osm_value] || (p.type === 'street' ? 'ulica' : '');
    // Photon extent is [west, north, east, south].
    const bounds = p.extent && [[p.extent[0], p.extent[3]], [p.extent[2], p.extent[1]]];
    // A village comes back both as its centre point and as its boundary, a river once per stretch: keep one.
    const same = (o) => p.osm_key === 'waterway' || (Math.abs(o.lat - lat) < 0.05 && Math.abs(o.lng - lng) < 0.07);
    const twin = places.find((o) => o.name === name && o.kind === kind && same(o));
    if (twin) {
      twin.bounds ||= bounds;
      continue;
    }
    places.push({
      id: `${p.osm_type}${p.osm_id}`,
      name,
      kind,
      lng,
      lat,
      bounds,
      zoom: ZOOM[p.type] ?? 14,
      detail: [kind, p.city !== name && p.city, p.type === 'house' && p.street, p.county].filter(Boolean).join(' · '),
    });
  }
  return places.slice(0, 6);
}
