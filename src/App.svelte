<script>
  import * as maplibregl from 'maplibre-gl';
  // MapLibre loads its worker relative to its own module, which Vite moves; hand it the bundled URL instead.
  import workerUrl from 'maplibre-gl/dist/maplibre-gl-worker.mjs?url';
  import { onMount } from 'svelte';
  import ChevronsLeftRight from '@lucide/svelte/icons/chevrons-left-right';
  import ChevronsUpDown from '@lucide/svelte/icons/chevrons-up-down';
  import ChevronDown from '@lucide/svelte/icons/chevron-down';
  import Columns2 from '@lucide/svelte/icons/columns-2';
  import Blend from '@lucide/svelte/icons/blend';
  import Camera from '@lucide/svelte/icons/camera';
  import Type from '@lucide/svelte/icons/type';
  import Share2 from '@lucide/svelte/icons/share-2';
  import TriangleAlert from '@lucide/svelte/icons/triangle-alert';
  import EraPicker from './EraPicker.svelte';
  import PhotoCard from './PhotoCard.svelte';
  import SearchBox from './SearchBox.svelte';
  import { available, byId, inBounds, nearestNational, sourceFor } from './lib/layers.js';
  import { captureDate } from './lib/capture.js';
  import { readView, writeView } from './lib/permalink.js';

  maplibregl.setWorkerUrl(workerUrl);

  const start = readView({ zoom: 14, lat: 48.1435, lng: 17.1077, left: '1880s', right: 'today' });

  let left = $state(byId(start.left) ? start.left : '1880s');
  let right = $state(byId(start.right) ? start.right : 'today');
  let center = $state({ lng: start.lng, lat: start.lat, zoom: start.zoom });
  let mode = $state('swipe');
  let opacity = $state(0.5);
  let split = $state(0.5);
  let portrait = $state(false);
  let picker = $state(null);
  let notice = $state('');
  let capture = $state({});
  let loading = $state({ top: false, bottom: false });
  let esriDown = $state(false);
  let hint = $state(!localStorage.getItem('kad:hinted'));
  let ready = $state(false);
  let labels = $state(localStorage.getItem('kad:labels') !== 'off');
  let photosOn = $state(localStorage.getItem('kad:photos') !== 'off');
  let photo = $state(null);
  // true or false once /geo answers; null until then (EU-only eras stay offered meanwhile).
  let eu = $state(null);

  let stage, topEl, bottomEl;
  let topMap, bottomMap;

  // In swipe mode the left era is the clipped top map; in opacity mode the older era goes on top.
  const leftYear = $derived(byId(left).year);
  const rightYear = $derived(byId(right).year);
  const topEra = $derived(mode === 'swipe' || leftYear <= rightYear ? left : right);
  const bottomEra = $derived(topEra === left ? right : left);

  const attribution = $derived(
    [
      ...new Set([byId(left).attribution, byId(right).attribution]),
      'Hranica © OpenStreetMap',
      'Názvy GeoNames (CC BY 4.0)',
      ...(photosOn ? ['Fotografie Wikimedia Commons a Ajapaik (licencia pri každej)'] : []),
    ].join(' · '),
  );

  const clip = $derived(
    mode === 'opacity'
      ? 'none'
      : portrait
        ? `inset(0 0 ${(1 - split) * 100}% 0)`
        : `inset(0 ${(1 - split) * 100}% 0 0)`,
  );

  // Orientation overlay drawn above every era: Slovakia's border and place names (bigger places from lower zooms).
  const labelRanks = [
    { rank: 4, minzoom: 12.5, size: 11, font: 'Noto Sans Regular' },
    { rank: 3, minzoom: 10.5, size: 12, font: 'Noto Sans Regular' },
    { rank: 2, minzoom: 8, size: 13, font: 'Noto Sans Bold' },
    { rank: 1, minzoom: 6, size: 15, font: 'Noto Sans Bold' },
  ];
  const emptyStyle = {
    version: 8,
    glyphs: 'https://tiles.openfreemap.org/fonts/{fontstack}/{range}.pbf',
    sources: {
      sk: { type: 'geojson', data: '/overlay/slovakia.geojson' },
      places: { type: 'geojson', data: '/overlay/places.geojson' },
    },
    layers: [
      { id: 'bg', type: 'background', paint: { 'background-color': '#ece7da' } },
      { id: 'sk-casing', type: 'line', source: 'sk', paint: { 'line-color': '#000', 'line-opacity': 0.35, 'line-width': 5 } },
      { id: 'sk-line', type: 'line', source: 'sk', paint: { 'line-color': '#ffd23f', 'line-width': 2, 'line-dasharray': [3, 1.5] } },
      ...labelRanks.map(({ rank, minzoom, size, font }) => ({
        id: `places-${rank}`,
        type: 'symbol',
        source: 'places',
        minzoom,
        filter: ['==', ['get', 'r'], rank],
        layout: { 'text-field': ['get', 'n'], 'text-font': [font], 'text-size': size, 'text-padding': 4 },
        paint: { 'text-color': '#fff', 'text-halo-color': 'rgba(20,16,8,0.85)', 'text-halo-width': 1.6 },
      })),
    ],
  };

  // Dims everything outside Slovakia: a world-sized polygon with the country cut out of it.
  const outsideMask = fetch('/overlay/slovakia.geojson')
    .then((r) => r.json())
    .then(({ geometry }) => ({
      type: 'Feature',
      properties: {},
      geometry: {
        type: 'Polygon',
        coordinates: [[[-180, -85], [180, -85], [180, 85], [-180, 85], [-180, -85]], geometry.coordinates[0]],
      },
    }));

  function addMask(map) {
    outsideMask.then((data) => {
      map.addSource('mask', { type: 'geojson', data });
      map.addLayer({ id: 'mask', type: 'fill', source: 'mask', paint: { 'fill-color': '#1d1b16', 'fill-opacity': 0.35 } }, 'sk-casing');
    });
  }

  // Historical photos with a confirmed place (scripts/build_photos.py), clustered when zoomed out.
  const photoLayers = ['photo-clusters', 'photo-count', 'photo-points'];

  function addPhotos(map) {
    map.addSource('photos', { type: 'geojson', data: '/overlay/photos.geojson', cluster: true, clusterRadius: 36, clusterMaxZoom: 15 });
    map.addLayer({
      id: 'photo-clusters', type: 'circle', source: 'photos', filter: ['has', 'point_count'],
      paint: {
        'circle-color': '#8a4b14', 'circle-stroke-color': '#fff', 'circle-stroke-width': 2,
        'circle-radius': ['step', ['get', 'point_count'], 13, 10, 17, 50, 22],
      },
    });
    map.addLayer({
      id: 'photo-count', type: 'symbol', source: 'photos', filter: ['has', 'point_count'],
      layout: { 'text-field': ['get', 'point_count_abbreviated'], 'text-font': ['Noto Sans Bold'], 'text-size': 12 },
      paint: { 'text-color': '#fff' },
    });
    map.addLayer({
      id: 'photo-points', type: 'circle', source: 'photos', filter: ['!', ['has', 'point_count']],
      // Confirmed places are solid; approximate ones are hollow.
      paint: {
        'circle-color': ['case', ['==', ['get', 'approx'], true], '#fff', ['to-boolean', ['get', 'now']], '#c2410c', '#8a4b14'],
        'circle-radius': ['case', ['==', ['get', 'approx'], true], 5.5, 7],
        'circle-stroke-color': ['case', ['==', ['get', 'approx'], true], '#8a4b14', '#fff'],
        'circle-stroke-width': ['case', ['==', ['get', 'approx'], true], 2.5, 2],
      },
    });
    map.on('click', 'photo-points', (e) => {
      const f = e.features[0];
      const p = { ...f.properties };
      // Older MapLibre versions hand nested objects back as JSON strings.
      if (typeof p.now === 'string') p.now = JSON.parse(p.now);
      [p.lng, p.lat] = f.geometry.coordinates;
      photo = p;
    });
    map.on('click', 'photo-clusters', async (e) => {
      const f = e.features[0];
      const zoom = await map.getSource('photos').getClusterExpansionZoom(f.properties.cluster_id);
      map.easeTo({ center: f.geometry.coordinates, zoom });
    });
    for (const id of ['photo-points', 'photo-clusters']) {
      map.on('mouseenter', id, () => (map.getCanvas().style.cursor = 'pointer'));
      map.on('mouseleave', id, () => (map.getCanvas().style.cursor = ''));
    }
  }

  function setPhotos(map, on) {
    for (const id of photoLayers) map.setLayoutProperty(id, 'visibility', on ? 'visible' : 'none');
  }

  function setLabels(map, on) {
    for (const { rank } of labelRanks) map.setLayoutProperty(`places-${rank}`, 'visibility', on ? 'visible' : 'none');
  }

  function makeMap(container) {
    const map = new maplibregl.Map({
      container,
      style: emptyStyle,
      center: [start.lng, start.lat],
      zoom: start.zoom,
      minZoom: 6,
      maxZoom: 19,
      maxBounds: [[14.5, 46.8], [25, 50.6]],
      attributionControl: false,
      dragRotate: false,
      pitchWithRotate: false,
    });
    map.touchZoomRotate.disableRotation();
    map.keyboard.disableRotation();
    return map;
  }

  function setEra(map, id) {
    if (map.era === id) return;
    if (map.getLayer('era')) map.removeLayer('era');
    if (map.getSource('era')) map.removeSource('era');
    map.addSource('era', sourceFor(byId(id)));
    // Below the overlay: under the outside mask once it exists, otherwise under the border.
    const below = map.getLayer('mask') ? 'mask' : 'sk-casing';
    map.addLayer({ id: 'era', type: 'raster', source: 'era', paint: { 'raster-fade-duration': 150 } }, below);
    map.era = id;
    if (id === 'esri') esriDown = false;
  }

  function track(map, key) {
    map.on('dataloading', () => (loading[key] = true));
    map.on('idle', () => (loading[key] = false));
    map.on('error', (e) => {
      if (map.era === 'esri' && [401, 403, 429].includes(e.error?.status)) esriDown = true;
    });
  }

  onMount(() => {
    const updateOrientation = () => (portrait = innerHeight > innerWidth && innerWidth < 800);
    updateOrientation();
    addEventListener('resize', updateOrientation);
    fetch('/geo')
      .then((r) => r.json())
      .then((g) => (eu = g.eu))
      .catch(() => {});

    bottomMap = makeMap(bottomEl);
    topMap = makeMap(topEl);
    let syncing = false;
    for (const [a, b] of [[topMap, bottomMap], [bottomMap, topMap]]) {
      a.on('move', () => {
        if (syncing) return;
        syncing = true;
        b.jumpTo({ center: a.getCenter(), zoom: a.getZoom() });
        syncing = false;
      });
    }
    topMap.on('moveend', () => {
      const c = topMap.getCenter();
      center = { lng: c.lng, lat: c.lat, zoom: topMap.getZoom() };
    });
    track(topMap, 'top');
    track(bottomMap, 'bottom');
    let loaded = 0;
    for (const m of [topMap, bottomMap]) {
      m.on('load', () => {
        addMask(m);
        addPhotos(m);
        ready = ++loaded === 2;
      });
    }

    const onHash = () => {
      const v = readView(center);
      if (byId(v.left)) left = v.left;
      if (byId(v.right)) right = v.right;
      topMap.jumpTo({ center: [v.lng, v.lat], zoom: v.zoom });
    };
    addEventListener('hashchange', onHash);
    return () => {
      removeEventListener('resize', updateOrientation);
      removeEventListener('hashchange', onHash);
      topMap.remove();
      bottomMap.remove();
    };
  });

  $effect(() => {
    if (!ready) return;
    setEra(topMap, topEra);
    setEra(bottomMap, bottomEra);
  });

  $effect(() => {
    localStorage.setItem('kad:labels', labels ? 'on' : 'off');
    if (ready) for (const m of [topMap, bottomMap]) setLabels(m, labels);
  });

  $effect(() => {
    localStorage.setItem('kad:photos', photosOn ? 'on' : 'off');
    if (!photosOn) photo = null;
    if (ready) for (const m of [topMap, bottomMap]) setPhotos(m, photosOn);
  });

  $effect(() => {
    if (ready) topMap.getContainer().style.opacity = mode === 'opacity' ? String(opacity) : '1';
  });

  // Keep the URL and the remembered view current.
  $effect(() => writeView({ ...center, left, right }));

  // A city era makes no sense outside its city, and an EU-only era does not load outside the EU:
  // fall back to the closest nationwide era this visitor can load.
  $effect(() => {
    const { lng, lat } = center;
    for (const side of ['left', 'right']) {
      const layer = byId(side === 'left' ? left : right);
      const outsideCity = layer.group !== 'national' && !inBounds(layer, lng, lat);
      if (!outsideCity && available(layer, eu)) continue;
      const next = nearestNational(layer.year, eu);
      notice = outsideCity
        ? `${layer.title} → ${next.label}: mimo mesta už nie sú dáta`
        : `${layer.label} → ${next.label}: letecká snímka GKÚ je dostupná len v EÚ`;
      if (side === 'left') left = next.id;
      else right = next.id;
      setTimeout(() => (notice = ''), 4000);
    }
  });

  // Capture dates for Esri layers, refreshed when the map stops moving.
  $effect(() => {
    const { lng, lat, zoom } = center;
    const ctrl = new AbortController();
    for (const id of new Set([left, right])) {
      const layer = byId(id);
      if (!layer.metadata) continue;
      captureDate(layer.metadata, lng, lat, zoom, ctrl.signal)
        .then((text) => (capture[id] = text))
        .catch(() => {});
    }
    return () => ctrl.abort();
  });

  function startDrag(e) {
    e.preventDefault();
    hint = false;
    localStorage.setItem('kad:hinted', '1');
    const el = e.currentTarget;
    el.setPointerCapture(e.pointerId);
    const move = (ev) => {
      const r = stage.getBoundingClientRect();
      const f = portrait ? (ev.clientY - r.top) / r.height : (ev.clientX - r.left) / r.width;
      split = Math.min(0.98, Math.max(0.02, f));
    };
    const up = () => {
      el.removeEventListener('pointermove', move);
      el.removeEventListener('pointerup', up);
      el.removeEventListener('pointercancel', up);
    };
    el.addEventListener('pointermove', move);
    el.addEventListener('pointerup', up);
    el.addEventListener('pointercancel', up);
  }

  function nudge(e) {
    const step = { ArrowLeft: -0.05, ArrowUp: -0.05, ArrowRight: 0.05, ArrowDown: 0.05 }[e.key];
    if (step) split = Math.min(0.98, Math.max(0.02, split + step));
  }

  function go(place) {
    if (place.bounds) topMap.fitBounds(place.bounds, { maxZoom: 16, duration: 1200 });
    else topMap.flyTo({ center: [place.lng, place.lat], zoom: place.zoom, duration: 1200 });
  }

  async function share() {
    const url = location.href;
    if (navigator.share) {
      try {
        await navigator.share({ title: 'Kedysi a dnes', url });
      } catch {}
      return;
    }
    await navigator.clipboard.writeText(url);
    notice = 'Odkaz je skopírovaný';
    setTimeout(() => (notice = ''), 2500);
  }

  function pick(id) {
    if (picker === 'left') left = id;
    else right = id;
    picker = null;
  }

  function useFallback(id) {
    if (left === 'esri') left = id;
    if (right === 'esri') right = id;
  }
</script>

<main class:portrait>
  <div class="stage" bind:this={stage}>
    <div class="map" bind:this={bottomEl}></div>
    <div class="map top" bind:this={topEl} style:clip-path={clip}></div>

    {#if mode === 'swipe'}
      <div
        class="divider"
        class:hint
        style={portrait ? `top:${split * 100}%` : `left:${split * 100}%`}
        onpointerdown={startDrag}
        onkeydown={nudge}
        role="slider"
        tabindex="0"
        aria-label="Deliaca čiara"
        aria-valuenow={Math.round(split * 100)}
      >
        <span class="knob">
          {#if portrait}<ChevronsUpDown size={20} />{:else}<ChevronsLeftRight size={20} />{/if}
        </span>
        {#if hint}<span class="hint-text">Potiahnite</span>{/if}
      </div>
    {/if}

    {#each [['left', left, loading[topEra === left ? 'top' : 'bottom']], ['right', right, loading[topEra === right ? 'top' : 'bottom']]] as [side, id, busy] (side)}
      {@const layer = byId(id)}
      <button class="era-card {side}" onclick={() => (picker = picker === side ? null : side)} aria-haspopup="dialog">
        <span class="era-head">
          <span class="era-label">{layer.label}</span>
          <span class="era-change"><ChevronDown size={16} /></span>
        </span>
        <span class="era-title">{layer.title}</span>
        {#if capture[id]}<span class="era-sub">{capture[id]}</span>{/if}
        {#if layer.warn}<span class="era-sub warn">{layer.note}</span>{/if}
        {#if center.zoom > layer.maxzoom + 1}<span class="era-sub">ostrejšie už nebude (max. priblíženie {layer.maxzoom})</span>{/if}
        {#if busy}<span class="busy"></span>{/if}
      </button>
    {/each}

    {#if esriDown}
      <div class="esri-down" role="alert">
        <p><TriangleAlert size={16} /> Satelitná snímka Esri je teraz nedostupná, skúste neskôr.</p>
        <span>
          {#each byId('esri').fallback as id (id)}
            <button onclick={() => useFallback(id)}>{byId(id).label}</button>
          {/each}
        </span>
      </div>
    {/if}

    {#if photo}
      <PhotoCard {photo} onclose={() => (photo = null)} />
    {/if}

    {#if picker}
      <EraPicker side={picker} selected={picker === 'left' ? left : right} {center} {eu} onpick={pick} onclose={() => (picker = null)} />
    {/if}
  </div>

  <div class="dock">
    <div class="brand"><span class="mark"></span>Kedysi a dnes</div>
    <SearchBox near={() => topMap.getCenter()} onpick={go} />
    <button class="share" onclick={share} aria-label="Zdieľať odkaz" title="Zdieľať odkaz">
      <Share2 size={16} /><span>Zdieľať</span>
    </button>
    <div class="seg" role="group" aria-label="Spôsob porovnania">
      <button aria-pressed={mode === 'swipe'} onclick={() => (mode = 'swipe')}><Columns2 size={16} />Slider</button>
      <button aria-pressed={mode === 'opacity'} onclick={() => (mode = 'opacity')}><Blend size={16} />Priehľadnosť</button>
    </div>
    {#if mode === 'opacity'}
      <!-- Older era on the left: dragging right fades it out and the newer one in. -->
      <label class="fade">
        <span>{byId(topEra).label}</span>
        <input
          type="range"
          min="0"
          max="1"
          step="0.01"
          bind:value={() => 1 - opacity, (v) => (opacity = 1 - v)}
          aria-label="Prechod medzi obdobiami"
        />
        <span>{byId(bottomEra).label}</span>
      </label>
    {/if}
    <button class="switch" role="switch" aria-checked={photosOn} onclick={() => (photosOn = !photosOn)}>
      <Camera size={16} /><span>Fotografie</span><span class="track"></span>
    </button>
    <button class="switch" role="switch" aria-checked={labels} onclick={() => (labels = !labels)}>
      <Type size={16} /><span>Názvy obcí</span><span class="track"></span>
    </button>
  </div>

  {#if notice}<div class="notice" role="status">{notice}</div>{/if}

  <footer class="attribution">{attribution}</footer>
</main>
