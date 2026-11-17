<script>
  import X from '@lucide/svelte/icons/x';
  import ArrowUpRight from '@lucide/svelte/icons/arrow-up-right';
  import BadgeCheck from '@lucide/svelte/icons/badge-check';
  import CircleDashed from '@lucide/svelte/icons/circle-dashed';

  let { photo, onclose } = $props();

  const proofText = $derived(
    {
      rephoto: 'Poloha overená: niekto to miesto odfotil znova',
      geotags: `Poloha overená: nezávisle ju určilo ${photo.geotaggers} ľudí`,
      commons: 'Poloha overená: zhoduje sa s polohou fotoaparátu na Commons',
      single: 'Poloha približná: na mapu ju umiestnil jeden človek',
      import: 'Poloha približná: prevzatá zo zdroja fotografie',
      camera: 'Poloha približná: podľa polohy fotoaparátu na Commons',
    }[photo.proof],
  );
  // Ajapaik gives the rephoto's licence as a Creative Commons URL, e.g. …/licenses/by/4.0/.
  const nowLicence = $derived.by(() => {
    const m = photo.now?.licenceUrl.match(/licenses\/([^/]+)\/([^/]+)/);
    return m ? `CC ${m[1].toUpperCase()} ${m[2]}` : 'licencia';
  });
  // Opens Google Street View at the photo's place (Maps URLs, no key); faces the camera direction when we know it.
  const streetView = $derived.by(() => {
    const params = new URLSearchParams({ api: '1', map_action: 'pano', viewpoint: `${photo.lat.toFixed(6)},${photo.lng.toFixed(6)}` });
    if (photo.azimuth != null) params.set('heading', String(Math.round((photo.azimuth + 360) % 360)));
    return `https://www.google.com/maps/@?${params}`;
  });
</script>

<svelte:window onkeydown={(e) => e.key === 'Escape' && onclose()} />

<aside class="photo-card" aria-label="Historická fotografia">
  <header>
    <div>
      <strong>{photo.title}</strong>
      {#if photo.date}<span class="date">{photo.date}</span>{/if}
    </div>
    <button class="close" onclick={onclose} aria-label="Zavrieť"><X size={18} /></button>
  </header>
  <div class="pics" class:pair={photo.now}>
    <figure>
      <a href={photo.page} target="_blank" rel="noopener"><img src={photo.img} alt={photo.title} /></a>
      <figcaption>
        Kedysi · {photo.author || 'neznámy autor'} ·
        {#if photo.licenceUrl}<a href={photo.licenceUrl} target="_blank" rel="noopener">{photo.licence}</a>{:else}{photo.licence}{/if}
        · <a href={photo.page} target="_blank" rel="noopener">Commons</a>
      </figcaption>
    </figure>
    {#if photo.now}
      <figure>
        <a href={photo.now.url} target="_blank" rel="noopener"><img src={photo.now.img} alt="To isté miesto dnes" /></a>
        <figcaption>
          Dnes{photo.now.date ? ` (${photo.now.date})` : ''} · {photo.now.by} ·
          <a href={photo.now.licenceUrl} target="_blank" rel="noopener">{nowLicence}</a> ·
          <a href={photo.now.url} target="_blank" rel="noopener">Ajapaik</a>
        </figcaption>
      </figure>
    {/if}
  </div>
  <div class="foot">
    <p class="proof" class:approx={photo.approx}>
      {#if photo.approx}<CircleDashed size={15} />{:else}<BadgeCheck size={15} />{/if}
      <span>{proofText}{photo.azimuth != null ? ` · pohľad na ${Math.round((photo.azimuth + 360) % 360)}°` : ''}</span>
    </p>
    <a class="streetview" class:primary={!photo.now} href={streetView} target="_blank" rel="noopener">
      {photo.now ? 'Street View' : 'Ako to vyzerá dnes? Street View'}
      <ArrowUpRight size={15} />
    </a>
  </div>
</aside>
