# Kedysi a dnes

A swipe map of Slovakia: one era on the left, another on the right, and a divider you drag between them. Ten nationwide eras (1780s military survey → today's aerial photo), plus historical photos and plans for Bratislava, Trenčín, Košice, Banská Bystrica and Žilina when the view is inside those cities.

- `catalog/layers.json`: every layer (tile URL, zoom limit, coverage box, attribution). The frontend and the Worker both read it; adding a layer is a data change. Set `"disabled": true` on a layer, or `"cityExtras": false`, to switch layers off.
- `src/`: Svelte 5 + MapLibre GL frontend (static, for Cloudflare Pages).
- `worker/`: Cloudflare Worker tile cache for the slow WMS servers (MŽP geocloud, city servers). `GET /t/{layer}/{z}/{x}/{y}` → 512 px GetMap, cached 30 days (7 for recent layers), at most 4 parallel upstream requests per server. Esri tiles never pass through it.
- `public/overlay/`: Slovakia's border (OpenStreetMap) and place names (GeoNames, CC BY 4.0) drawn above every era; rebuild with `python3 scripts/build_overlay.py`.
- `scripts/refresh_catalog.py`: weekly check (GitHub Actions, `.github/workflows/catalog.yml`). Marks layers whose sample tile fails as `broken` (the site and Worker hide them), updates the Esri capture-date release, and reports new layers at the sources in a pull request.

## Develop

```sh
npm install
npm run worker:dev                 # tile cache on :8787
VITE_TILE_PROXY=/tiles npm run dev # frontend; /tiles is proxied to the Worker
```

Without `VITE_TILE_PROXY` the browser calls the WMS servers directly, which also works, only slower.

## Deploy (Cloudflare)

1. `npx wrangler login`, then `npm run worker:deploy`. Note the Worker URL.
2. Create an ArcGIS Location Platform account (free tier: 2M basemap tiles a month), make an API key with the basemap privilege, restrict it to the site's domain, and leave pay-as-you-go off.
3. Create a Pages project from this repository: build `npm run build`, output `dist`, environment variables `VITE_TILE_PROXY=<worker URL>` and `VITE_ESRI_KEY=<key>`.

Without `VITE_ESRI_KEY` the "today" layer uses Esri's keyless URL, which Esri's terms allow only inside Esri software: fine for local development, not for the public site.

## Licences

MŽP SR maps are CC0 / CC BY 4.0, Landsat (NASA GIBS) is open data. Esri imagery is shown under the Esri terms with attribution and is never cached. City photos and plans are © their providers with no open licence; each city can be switched off in the catalog.
