<script>
  import { setConsent } from './lib/analytics.js';

  let { onclose } = $props();

  function answer(accepted) {
    setConsent(accepted);
    onclose();
  }
</script>

<div class="consent" role="dialog" aria-label="Súhlas s cookies">
  <p>
    Návštevnosť meriame cez PostHog, aby sme vedeli, ktoré mapy a miesta vás zaujímajú. S vaším súhlasom použijeme
    cookie a spoznáme, keď sa vrátite. Bez neho počítame návštevy anonymne, bez cookies.
  </p>
  <span class="actions">
    <button onclick={() => answer(false)}>Odmietnuť</button>
    <button class="accept" onclick={() => answer(true)}>Prijať</button>
  </span>
</div>

<style>
  .consent {
    position: absolute; z-index: 30; left: 50%; bottom: 12px; transform: translateX(-50%);
    width: min(520px, calc(100vw - 24px)); display: flex; align-items: center; gap: 14px; padding: 12px 14px;
    background: var(--surface); border-radius: var(--r); box-shadow: var(--shadow-lg);
  }
  p { margin: 0; font-size: 13px; color: var(--text-2); }
  .actions { display: flex; flex-direction: column; gap: 6px; }
  button {
    height: 34px; padding: 0 14px; white-space: nowrap; border: 1px solid var(--line-strong); border-radius: var(--r-sm);
    background: var(--surface); font-weight: 500; transition: background 0.15s;
  }
  button:hover { background: var(--subtle); }
  .accept { background: var(--accent); border-color: var(--accent); color: #fff; }
  .accept:hover { background: #a8441f; }
  @media (max-width: 640px) {
    .consent { flex-direction: column; align-items: stretch; }
    .actions { flex-direction: row-reverse; }
    .actions button { flex: 1; }
  }
</style>
