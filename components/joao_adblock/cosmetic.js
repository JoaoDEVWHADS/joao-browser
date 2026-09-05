// Runs in an isolated world; filter data is compiled, never fetched as code.
(() => {
  'use strict';
  const rules = /* RULES */ [];
  const documentExceptions = /* EXCEPTIONS */ [];
  const host = location.hostname;
  const matches = domain => host === domain || host.endsWith('.' + domain);
  const applies = domains => {
    if (domains.some(domain => domain.startsWith('~') && matches(domain.slice(1)))) return false;
    const included = domains.filter(domain => !domain.startsWith('~'));
    return !included.length || included.some(matches);
  };
  const matchingExceptions = documentExceptions.filter(([pattern, domains, , matchCase]) =>
    applies(domains) && new RegExp(pattern, matchCase ? '' : 'i').test(location.href));
  if (matchingExceptions.some(rule => !rule[2])) return;
  const genericDisabled = matchingExceptions.length !== 0;
  const selected = rules.filter(rule => applies(rule[0]) &&
    (!genericDisabled || rule[0].some(domain => !domain.startsWith('~'))));
  const exceptions = new Set(selected.filter(rule => rule[2]).map(rule => rule[1]));
  const selectors = selected.filter(rule => !rule[2] && !exceptions.has(rule[1]));
  return selectors.map(([, selector]) => selector + '{display:none!important}').join('\n');
})();
