import { describe, test, expect, afterEach } from 'bun:test';
import { launchBrowser } from '../cli/engine/engines/browser/detect-url.mjs';

// launchBrowser prefers the system-installed Chrome on Windows to dodge the
// bundled-Chrome GPU crash-loop (issue #372), and keeps the pinned bundled
// build everywhere else. The function takes the puppeteer module as a
// parameter, so a fake lets us assert the launch strategy without a real
// browser or a real OS.

const realPlatform = Object.getOwnPropertyDescriptor(process, 'platform');

function setPlatform(value) {
  Object.defineProperty(process, 'platform', { value, configurable: true });
}

afterEach(() => {
  Object.defineProperty(process, 'platform', realPlatform);
});

function makePuppeteer({ failChannel = false } = {}) {
  const calls = [];
  const fakeBrowser = { __fake: true };
  return {
    calls,
    fakeBrowser,
    mod: {
      default: {
        async launch(opts) {
          calls.push(opts);
          if (failChannel && opts.channel === 'chrome') {
            throw new Error('Could not find Chrome (channel: chrome)');
          }
          return fakeBrowser;
        },
      },
    },
  };
}

describe('launchBrowser', () => {
  test('Windows: prefers system Chrome via channel:chrome', async () => {
    setPlatform('win32');
    const p = makePuppeteer();
    const browser = await launchBrowser(p.mod, { headless: true, args: ['--foo'] });

    expect(browser).toBe(p.fakeBrowser);
    expect(p.calls).toHaveLength(1);
    expect(p.calls[0].channel).toBe('chrome');
    expect(p.calls[0].headless).toBe(true);
    expect(p.calls[0].args).toEqual(['--foo']);
  });

  test('Windows: falls back to bundled when system Chrome is unavailable', async () => {
    setPlatform('win32');
    const p = makePuppeteer({ failChannel: true });
    const browser = await launchBrowser(p.mod, { headless: true, args: [] });

    expect(browser).toBe(p.fakeBrowser);
    expect(p.calls).toHaveLength(2);
    expect(p.calls[0].channel).toBe('chrome'); // first attempt
    expect(p.calls[1].channel).toBeUndefined(); // fallback: bundled, no channel
  });

  test('non-Windows: uses bundled Chrome directly, no channel', async () => {
    setPlatform('linux');
    const p = makePuppeteer();
    const browser = await launchBrowser(p.mod, { headless: true, args: [] });

    expect(browser).toBe(p.fakeBrowser);
    expect(p.calls).toHaveLength(1);
    expect(p.calls[0].channel).toBeUndefined();
  });

  test('non-Windows: never attempts channel:chrome even if it would succeed', async () => {
    setPlatform('darwin');
    const p = makePuppeteer();
    await launchBrowser(p.mod, {});

    expect(p.calls.every(c => c.channel === undefined)).toBe(true);
  });
});
