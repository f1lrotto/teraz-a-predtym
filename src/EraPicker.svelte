<script>
  import X from '@lucide/svelte/icons/x';
  import Check from '@lucide/svelte/icons/check';
  import { available, erasAt } from './lib/layers.js';

  let { side, selected, center, eu, onpick, onclose } = $props();
  const eras = $derived(erasAt(center.lng, center.lat));
</script>

<svelte:window onkeydown={(e) => e.key === 'Escape' && onclose()} />

<div class="backdrop" onclick={onclose} role="presentation"></div>
<div class="picker {side}" role="dialog" aria-label="Vyberte obdobie">
  <header>
    <strong>{side === 'left' ? 'Ľavá' : 'Pravá'} strana</strong>
    <button class="close" onclick={onclose} aria-label="Zavrieť"><X size={18} /></button>
  </header>
  <ul>
    {#each eras.national as { layer, here } (layer.id)}
      <li>
        <button class:active={layer.id === selected} disabled={!here || !available(layer, eu)} onclick={() => onpick(layer.id)}>
          <span class="label">{layer.label}</span>
          <span class="title">{layer.title}</span>
          {#if layer.id === selected}<span class="check"><Check size={16} /></span>{/if}
          {#if !available(layer, eu)}<span class="none">dostupné len v EÚ</span>
          {:else if !here}<span class="none">tu nie sú dáta</span>
          {:else if layer.note}<span class="note">{layer.note}</span>{/if}
        </button>
      </li>
    {/each}
  </ul>
  {#each eras.cities as city (city.group)}
    <h3>{city.name}</h3>
    <ul>
      {#each city.layers as layer (layer.id)}
        <li>
          <button class:active={layer.id === selected} onclick={() => onpick(layer.id)}>
            <span class="label">{layer.label}</span>
            <span class="title">{layer.title}</span>
            {#if layer.id === selected}<span class="check"><Check size={16} /></span>{/if}
          </button>
        </li>
      {/each}
    </ul>
  {/each}
</div>

<style>
  .backdrop { position: fixed; inset: 0; z-index: 20; }
  .picker {
    position: absolute; z-index: 21; top: 12px; width: min(360px, calc(100vw - 24px));
    max-height: calc(100% - 24px); overflow: auto; padding: 0 6px 6px; color: var(--text);
    background: var(--surface); border-radius: var(--r); box-shadow: var(--shadow-lg);
  }
  .picker.left { left: 12px; }
  .picker.right { right: 12px; }
  header {
    position: sticky; top: 0; z-index: 1; display: flex; justify-content: space-between; align-items: center;
    margin: 0 -6px; padding: 10px 10px 8px 18px; background: var(--surface);
  }
  header strong { font-size: 15px; font-weight: 600; letter-spacing: -0.01em; }
  .close {
    width: 30px; height: 30px; display: grid; place-items: center; background: none; border: 0; border-radius: 8px;
    color: var(--muted);
  }
  .close:hover { color: var(--text); background: var(--subtle); }
  h3 { margin: 10px 12px 4px; font-size: 12px; font-weight: 500; color: var(--muted); }
  ul { list-style: none; margin: 0; padding: 0; }
  li button {
    display: grid; grid-template-columns: 58px 1fr 16px; column-gap: 10px; align-items: baseline; width: 100%;
    text-align: left; background: none; border: 0; border-radius: var(--r-sm); padding: 8px 12px; color: inherit;
    font: inherit; cursor: pointer;
  }
  li button:hover:not(:disabled) { background: var(--subtle); }
  li button.active { background: var(--accent-soft); }
  li button:disabled { opacity: 0.45; cursor: default; }
  .label { font-weight: 600; font-variant-numeric: tabular-nums; }
  .title { color: var(--text-2); }
  .active .label, .active .title { color: var(--accent); }
  .check { grid-column: 3; grid-row: 1; align-self: center; color: var(--accent); }
  .note, .none { grid-column: 2 / 4; font-size: 12px; color: var(--muted); }
  @media (orientation: portrait) and (max-width: 800px) {
    .picker.right { top: auto; bottom: 12px; }
  }
</style>
