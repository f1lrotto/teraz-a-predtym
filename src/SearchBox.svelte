<script>
  import Search from '@lucide/svelte/icons/search';
  import X from '@lucide/svelte/icons/x';
  import LoaderCircle from '@lucide/svelte/icons/loader-circle';
  import { suggest } from './lib/search.js';

  // near() returns the map centre, so nearby places rank first; onpick(place) moves the map there.
  let { near, onpick } = $props();

  let input;
  let query = $state('');
  let open = $state(false);
  let places = $state([]);
  let status = $state(''); // '', 'loading', 'empty' or 'error'
  let active = $state(0);
  // Enter pressed before the suggestions arrived: take the first one when they do.
  let pickWhenReady = false;
  const cache = new Map();

  const listed = $derived(open && (places.length > 0 || status === 'empty' || status === 'error'));

  $effect(() => {
    const q = query.trim();
    if (!open || q.length < 2) {
      places = [];
      status = '';
      return;
    }
    const key = q.toLowerCase();
    if (cache.has(key)) return show(cache.get(key));
    status = 'loading';
    const ctrl = new AbortController();
    // Ask only once typing pauses.
    const timer = setTimeout(() => {
      suggest(q, near(), ctrl.signal)
        .then((found) => {
          cache.set(key, found);
          show(found);
        })
        .catch((e) => {
          if (e.name !== 'AbortError') status = 'error';
        });
    }, 250);
    return () => {
      clearTimeout(timer);
      ctrl.abort();
    };
  });

  function show(found) {
    places = found;
    active = 0;
    status = found.length ? '' : 'empty';
    if (pickWhenReady && found.length) pick(found[0]);
    pickWhenReady = false;
  }

  function pick(place) {
    onpick(place);
    query = place.name;
    open = false;
    input.blur();
  }

  function submit(e) {
    e.preventDefault();
    if (status !== 'loading' && places[active]) pick(places[active]);
    else if (query.trim().length >= 2) {
      open = true;
      pickWhenReady = true;
    }
  }

  function onkeydown(e) {
    if ((e.key === 'ArrowDown' || e.key === 'ArrowUp') && places.length) {
      e.preventDefault();
      active = (active + (e.key === 'ArrowDown' ? 1 : -1) + places.length) % places.length;
    } else if (e.key === 'Escape') {
      open = false;
    }
  }
</script>

<form class="search" role="search" onsubmit={submit}>
  <span class="icon" class:spin={status === 'loading'}>
    {#if status === 'loading'}<LoaderCircle size={16} />{:else}<Search size={16} />{/if}
  </span>
  <input
    bind:this={input}
    bind:value={query}
    oninput={() => (open = true)}
    onfocus={() => (open = true)}
    onblur={() => (open = false)}
    {onkeydown}
    type="text"
    placeholder="Hľadať obec, ulicu, hrad…"
    autocomplete="off"
    spellcheck="false"
    role="combobox"
    aria-label="Hľadať miesto"
    aria-autocomplete="list"
    aria-controls="search-list"
    aria-expanded={listed}
    aria-activedescendant={listed && places.length ? `place-${active}` : undefined}
  />
  {#if query}
    <button
      type="button"
      class="clear"
      aria-label="Vymazať"
      onmousedown={(e) => e.preventDefault()}
      onclick={() => {
        query = '';
        input.focus();
      }}
    >
      <X size={16} />
    </button>
  {/if}
  {#if listed}
    <ul class="results" id="search-list" role="listbox" aria-label="Návrhy miest">
      {#each places as place, i (place.id)}
        <!-- The input handles the keyboard (combobox pattern); options only take the pointer. -->
        <!-- svelte-ignore a11y_click_events_have_key_events -->
        <li
          id="place-{i}"
          role="option"
          aria-selected={i === active}
          onmousedown={(e) => e.preventDefault()}
          onmousemove={() => (active = i)}
          onclick={() => pick(place)}
        >
          <span class="name">{place.name}</span>
          {#if place.detail}<span class="detail">{place.detail}</span>{/if}
        </li>
      {/each}
      {#if status === 'empty'}<li class="msg">Nič sa nenašlo</li>{/if}
      {#if status === 'error'}<li class="msg">Vyhľadávanie teraz nefunguje, skúste neskôr</li>{/if}
    </ul>
  {/if}
</form>

<style>
  .search { position: relative; }
  .icon {
    position: absolute; left: 12px; top: 50%; margin-top: -8px; display: flex; color: var(--muted); pointer-events: none;
  }
  .icon.spin { animation: spin 0.8s linear infinite; }
  @keyframes spin { to { transform: rotate(360deg); } }
  input {
    width: 100%; height: 38px; padding: 0 36px 0 38px; color: var(--text); background: var(--subtle);
    border: 1px solid transparent; border-radius: var(--r-sm); outline: none;
    transition: border-color 0.15s, background 0.15s, box-shadow 0.15s;
  }
  input::placeholder { color: var(--muted); }
  input:hover { background: var(--hover); }
  input:focus { background: var(--surface); border-color: var(--accent); box-shadow: 0 0 0 3px var(--accent-soft); }
  .clear {
    position: absolute; right: 4px; top: 4px; width: 30px; height: 30px; display: grid; place-items: center;
    border: 0; border-radius: 8px; background: none; color: var(--muted);
  }
  .clear:hover { color: var(--text); background: var(--hover); }
  .results {
    position: absolute; z-index: 30; left: 0; right: 0; bottom: calc(100% + 8px); margin: 0; padding: 6px;
    list-style: none; background: var(--surface); border-radius: var(--r); box-shadow: var(--shadow-lg);
  }
  li[role='option'] {
    display: flex; flex-direction: column; gap: 1px; padding: 8px 10px; border-radius: var(--r-sm); cursor: pointer;
  }
  li[aria-selected='true'] { background: var(--subtle); }
  .name { font-weight: 500; }
  .detail { font-size: 12px; color: var(--muted); }
  .msg { padding: 8px 10px; color: var(--muted); }
</style>
