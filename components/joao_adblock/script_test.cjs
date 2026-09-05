'use strict';
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const youtube = fs.readFileSync(__dirname + '/youtube.js', 'utf8');
(async () => {
  class Response { async json() { return this.payload; } }
  const context = vm.createContext({window: {}, Response});
  vm.runInContext(youtube, context);
  const result = vm.runInContext(`JSON.parse('{"videoDetails":{"videoId":"test"},"adPlacements":[1],"playerAds":[2],"adSlots":[3],"streamingData":{"formats":[1]}}')`, context);
  assert.equal(result.adPlacements, undefined);
  assert.equal(result.playerAds, undefined);
  assert.equal(result.adSlots, undefined);
  assert.equal(result.streamingData.formats[0], 1);
  assert.equal(vm.runInContext('JSON.parse(\'{"playerAds":[2]}\').playerAds[0]', context), 2);
  assert.equal(vm.runInContext('JSON.parse("null")', context), null);
  assert.throws(() => vm.runInContext('JSON.parse("invalid")', context));
  vm.runInContext('window.ytInitialPlayerResponse = {playabilityStatus: {}, playerAds: [1]}', context);
  assert.equal(context.window.ytInitialPlayerResponse.playerAds, undefined);
  const response = new Response();
  response.payload = {streamingData: {}, adSlots: [1]};
  assert.equal((await response.json()).adSlots, undefined);
  // JSON revivers still run and nested, unrelated data is preserved.
  assert.equal(vm.runInContext('JSON.parse("2", (k,v) => v + 1)', context), 3);

  const rules = [[[], '.advert', false], [['~example.com'], '.excluded', false],
    [['example.com'], '.advert', true], [['example.com'], '.specific', false],
    [['other.com'], '.other', false]];
  const cosmetic = fs.readFileSync(__dirname + '/cosmetic.js', 'utf8')
    .replace('/* RULES */ []', JSON.stringify(rules));
  const evaluate = script => vm.runInNewContext(script,
    {location: {hostname: 'www.example.com', href: 'https://www.example.com/'}});
  assert.equal(evaluate(cosmetic), '.specific{display:none!important}');
  const genericException = cosmetic.replace('/* EXCEPTIONS */ []',
    JSON.stringify([['', [], true, false]]));
  assert.equal(evaluate(genericException), '.specific{display:none!important}');
  const hideException = cosmetic.replace('/* EXCEPTIONS */ []',
    JSON.stringify([['', [], false, false]]));
  assert.equal(evaluate(hideException), undefined);
  console.log('PASS: YouTube player responses, fetch JSON, globals, revivers, ordinary data and cosmetic exceptions');
})();
