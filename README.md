# Kedysi a dnes

A swipe map of Slovakia: one era on the left, another on the right, and a divider you drag between them. Ten nationwide eras (1780s military survey → today's aerial photo), plus historical photos and plans for Bratislava, Trenčín, Košice, Banská Bystrica and Žilina when the view is inside those cities.

- `catalog/layers.json`: every layer (tile URL, zoom limit, coverage box, attribution). The frontend and the Worker both read it; adding a layer is a data change. Set `"disabled": true` on a layer, or `"cityExtras": false`, to switch layers off.
- `src/`: Svelte 5 + MapLibre GL frontend, built to `dist/`. Place search suggests as you type from [Photon](https://photon.komoot.io) (komoot's public OpenStreetMap geocoder, best effort); Nominatim's usage policy forbids autocomplete.
- `worker/` and `wrangler.toml`: one Cloudflare Worker that serves `dist/` as static assets and runs the tile cache for the slow WMS servers (MŽP geocloud, city servers). `GET /t/{layer}/{z}/{x}/{y}` → 512 px GetMap, cached 30 days (7 for recent layers). Esri and GKÚ orthophoto tiles never pass through it: the browser loads them live. `GET /geo` tells the page whether the visitor is in the EU (Cloudflare's `request.cf.isEUCountry`).
- `src/lib/analytics.js`: usage analytics in PostHog (EU cloud, project "Kedysi"), sent through the Worker at `/k/` so ad blockers leave it alone. Visitors are counted without cookies until they accept the cookie banner. Build with `VITE_POSTHOG_KEY=<project token>`; without it nothing is sent and no banner is shown.
- `public/overlay/`: Slovakia's border (OpenStreetMap) and place names (GeoNames, CC BY 4.0) drawn above every era; rebuild with `python3 scripts/build_overlay.py`.
- `public/overlay/photos.geojson`: historical photos (Wikimedia Commons via Ajapaik, and Commons photos with a camera location), each with its licence and credit. Solid markers have a confirmed place, hollow ones an approximate place; every photo links to Google Street View at its spot. Rebuild with `python3 scripts/build_photos.py`.
- `scripts/refresh_catalog.py`: weekly check (GitHub Actions, `.github/workflows/catalog.yml`). Marks layers whose sample tile fails as `broken` (the site and Worker hide them), updates the Esri capture-date release, and reports new layers at the sources in a pull request.

## Develop

```sh
npm install
npm run dev:tiles   # builds the site and runs the Worker (tile cache) on :8787
npm run dev         # frontend with hot reload; /t/ requests are proxied to the Worker
```

## Deploy (Cloudflare)

`npm run deploy` builds the site and deploys the Worker with `wrangler deploy` (log in first, or set `CLOUDFLARE_API_TOKEN`). Serve it on a custom domain: the tile cache uses the Cache API, which works on custom domains, not on `*.workers.dev`.

"Dnes" (today) is GKÚ's national orthophoto, loaded live from `zbgis.skgeodesy.sk`. That server refuses connections from outside Europe, so the layer is marked `"euOnly"`: outside the EU the picker disables it and the page switches to the Esri satellite era ("Satelit").

For the Esri satellite era, create an ArcGIS Location Platform account (free tier: 2M basemap tiles a month), make an API key with the basemap privilege, restrict it to the site's domain, leave pay-as-you-go off, and build with `VITE_ESRI_KEY=<key>`. Without it the layer uses Esri's keyless URL, which Esri's terms allow only inside Esri software.

## Licences

MŽP SR maps are CC0 / CC BY 4.0, Landsat (NASA GIBS) is open data. The GKÚ orthophoto may be used as a web basemap with the credit "GKÚ Bratislava, NLC". Esri imagery is shown under the Esri terms with attribution. Neither is cached. City photos and plans are © their providers with no open licence; each city can be switched off in the catalog. Historical photos are public domain or CC BY / CC BY-SA, credited on each photo card.
