// Browser-owned document-start intervention, limited to YouTube player data.
(() => {
  'use strict';
  const clean = value => {
    if (!value || typeof value !== 'object') return value;
    // Avoid recursively rewriting unrelated account or video metadata.
    if ('playabilityStatus' in value || 'streamingData' in value || 'videoDetails' in value) {
      delete value.adPlacements;
      delete value.playerAds;
      delete value.adSlots;
    }
    return value;
  };
  let response = clean(window.ytInitialPlayerResponse);
  try {
    Object.defineProperty(window, 'ytInitialPlayerResponse', {
      configurable: true,
      get: () => response,
      set: value => { response = clean(value); },
    });
  } catch (_) {}
  const originalParse = JSON.parse;
  JSON.parse = new Proxy(originalParse, {
    apply(target, receiver, args) { return clean(Reflect.apply(target, receiver, args)); },
  });
  const originalJson = Response.prototype.json;
  Response.prototype.json = new Proxy(originalJson, {
    apply(target, receiver, args) {
      return Reflect.apply(target, receiver, args).then(clean);
    },
  });
})();
