const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');

const source = fs.readFileSync(__dirname + '/static/language-menu.js', 'utf8');

function setup({ finePointer = true } = {}) {
  const documentListeners = {};
  const menuListeners = {};
  let open = true;
  let focusCount = 0;
  const summary = { focus() { focusCount += 1; } };
  const menu = {
    get open() { return open; },
    contains(target) { return target === this || target === summary; },
    removeAttribute(name) { if (name === 'open') open = false; },
    querySelector(selector) { return selector === 'summary' ? summary : null; },
    addEventListener(name, listener) { menuListeners[name] = listener; },
  };
  const document = {
    querySelector(selector) { return selector === '.language-menu' ? menu : null; },
    addEventListener(name, listener) { documentListeners[name] = listener; },
  };
  const windowListeners = {};
  let timer;
  const window = {
    matchMedia() { return { matches: finePointer }; },
    setTimeout(listener, milliseconds) { timer = { listener, milliseconds }; return 1; },
    clearTimeout() { timer = undefined; },
    addEventListener(name, listener) { windowListeners[name] = listener; },
  };
  vm.runInNewContext(source, { document, window });
  return {
    summary, documentListeners, windowListeners, menuListeners,
    reopen() { open = true; },
    isOpen() { return open; },
    focusCount() { return focusCount; },
    timer() { return timer; },
  };
}

const desktop = setup();
desktop.windowListeners.pointerdown({ target: {}, composedPath() { return []; } });
assert.equal(desktop.isOpen(), false, 'outside pointer press closes the menu');

desktop.reopen();
desktop.windowListeners.pointerdown({ target: desktop.summary, composedPath() { return [desktop.summary]; } });
assert.equal(desktop.isOpen(), true, 'presses inside the menu keep it open');

desktop.windowListeners.click({ target: {}, composedPath() { return []; } });
assert.equal(desktop.isOpen(), false, 'outside click closes the menu when pointer events are unavailable');

desktop.reopen();
desktop.documentListeners.keydown({ key: 'Escape' });
assert.equal(desktop.isOpen(), false, 'Escape closes the menu');
assert.equal(desktop.focusCount(), 1, 'Escape returns focus to the summary');

desktop.reopen();
desktop.menuListeners.mouseleave();
assert.equal(desktop.timer().milliseconds, 120, 'mouse leave uses a short dismissal delay');
desktop.timer().listener();
assert.equal(desktop.isOpen(), false, 'mouse leave closes the menu');

const touch = setup({ finePointer: false });
assert.equal(touch.menuListeners.mouseleave, undefined, 'touch devices do not get mouse-leave dismissal');

console.log('PASS: language menu outside press, Escape, desktop mouse leave, and touch behavior');
