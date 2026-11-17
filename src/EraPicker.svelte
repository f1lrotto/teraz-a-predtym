<script>
  import { available, erasAt } from './lib/layers.js';

  let { side, selected, center, eu, onpick, onclose } = $props();
  const eras = $derived(erasAt(center.lng, center.lat));
</script>

<svelte:window onkeydown={(e) => e.key === 'Escape' && onclose()} />

<div class="backdrop" onclick={onclose} role="presentation"></div>
<div class="picker {side}" role="dialog" aria-label="Vyberte obdobie">
  <header>
    <strong>{side === 'left' ? 'Ľavá' : 'Pravá'} strana</strong>
    <button class="close" onclick={onclose} aria-label="Zavrieť">✕</button>
  </header>
  <ul>
    {#each eras.national as { layer, here } (layer.id)}
      <li>
        <button class:active={layer.id === selected} disabled={!here || !available(layer, eu)} onclick={() => onpick(layer.id)}>
          <span class="label">{layer.label}</span>
          <span class="title">{layer.title}</span>
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
          </button>
        </li>
      {/each}
    </ul>
  {/each}
</div>

<style>
  .backdrop { position: fixed; inset: 0; z-index: 20; }
  .picker {
    position: absolute; z-index: 21; top: 64px; width: min(340px, calc(100vw - 24px));
    max-height: calc(100% - 120px); overflow: auto; background: var(--panel); color: var(--ink);
    border-radius: 12px; box-shadow: var(--shadow); padding: 8px 0 12px;
  }
  .picker.left { left: 12px; }
  .picker.right { right: 12px; }
  header { display: flex; justify-content: space-between; align-items: center; padding: 4px 14px 8px; }
  .close { background: none; border: 0; font-size: 16px; color: var(--muted); padding: 4px; }
  h3 { margin: 12px 14px 4px; font-size: 12px; text-transform: uppercase; letter-spacing: 0.06em; color: var(--accent); }
  ul { list-style: none; margin: 0; padding: 0; }
  li button {
    display: grid; grid-template-columns: 64px 1fr; column-gap: 8px; width: 100%; text-align: left;
    background: none; border: 0; padding: 8px 14px; color: inherit; font: inherit; cursor: pointer;
  }
  li button:hover:not(:disabled) { background: var(--hover); }
  li button.active { background: var(--selected); }
  li button:disabled { opacity: 0.45; cursor: default; }
  .label { font-weight: 700; font-variant-numeric: tabular-nums; }
  .note, .none { grid-column: 2; font-size: 12px; color: var(--muted); }
  @media (orientation: portrait) and (max-width: 800px) {
    .picker.right { top: auto; bottom: 64px; }
  }
</style>
