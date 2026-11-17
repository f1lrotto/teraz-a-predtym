// Usage analytics (PostHog, EU cloud), sent through the Worker's /k/ proxy so ad blockers leave it alone.
// Until a visitor accepts the cookie banner, PostHog counts them without cookies or storage (an anonymous daily hash
// made on PostHog's servers); after "Prijať" it keeps an ID in a cookie, so returning visitors are recognised.
// Without VITE_POSTHOG_KEY (local dev) nothing is sent and no banner is shown.
const KEY = import.meta.env.VITE_POSTHOG_KEY || '';
export const enabled = !!KEY;

// The SDK is a separate chunk loaded next to the map, not in front of it; calls made meanwhile wait for it, in order.
const ready = KEY
  ? import('posthog-js').then(({ default: posthog }) => {
      posthog.init(KEY, {
        api_host: `${location.origin}/k`,
        ui_host: 'https://eu.posthog.com',
        defaults: '2026-08-30',
        // The URL hash changes on every map move, so App sends the one pageview itself, once /geo has answered.
        capture_pageview: false,
        capture_pageleave: true,
        person_profiles: 'identified_only',
        persistence: 'localStorage+cookie',
        cookieless_mode: 'on_reject',
        // Cookieless until the visitor accepts; without this PostHog sends nothing while the banner is unanswered.
        opt_out_capturing_by_default: true,
        // Both maps are WebGL canvases, which replays do not show.
        disable_session_recording: true,
      });
      return posthog;
    })
  : null;

// Everything passed to context(), kept to register again after a consent change.
const registered = {};

function use(fn) {
  ready?.then(fn).catch(() => {});
}

// Calls back with 'granted', 'denied' or 'pending' (banner not answered yet).
export function onConsent(fn) {
  use((posthog) => fn(posthog.get_explicit_consent_status()));
}

// Switching between the cookieless and the stored ID drops the registered context, so register it again.
export function setConsent(accepted) {
  use((posthog) => {
    if (accepted) posthog.opt_in_capturing({ captureProperties: registered });
    else posthog.opt_out_capturing();
    posthog.register(registered);
  });
}

export function track(event, props) {
  use((posthog) => posthog.capture(event, props));
}

// Properties sent with every later event, e.g. the eras on screen.
export function context(props) {
  Object.assign(registered, props);
  use((posthog) => posthog.register(props));
}
