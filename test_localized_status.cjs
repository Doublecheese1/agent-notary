const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');

const script = fs.readFileSync('static/localized-status.js', 'utf8');
const tick = () => new Promise(resolve => setImmediate(resolve));

async function check(config, expected) {
  const status = {
    textContent: 'Checking',
    dataset: { open: 'OPEN', limited: 'LIMITED', closed: 'CLOSED', unknown: 'UNKNOWN' },
  };
  const sandbox = {
    document: { querySelector: () => status },
    fetch: async () => {
      if (config === null) throw new Error('Unavailable');
      return { ok: true, json: async () => config };
    },
  };
  vm.runInNewContext(script, sandbox);
  await tick();
  await tick();
  assert.equal(status.textContent, expected);
}

(async () => {
  await check({ enabled: true, accepting_funds: true, public_access: true, paused: false }, 'OPEN');
  await check({ enabled: true, accepting_funds: false, public_access: true, paused: false }, 'LIMITED');
  await check({ enabled: true, accepting_funds: true, public_access: false, paused: false }, 'CLOSED');
  await check({ enabled: true, accepting_funds: true, public_access: true, paused: true }, 'CLOSED');
  await check(null, 'UNKNOWN');
  console.log('Localized status states: OK');
})().catch(error => { console.error(error); process.exit(1); });
