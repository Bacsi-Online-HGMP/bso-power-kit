import assert from 'node:assert/strict';
import test from 'node:test';
import path from 'node:path';

import {
  buildGenerationPreflight,
  runGenerationPreflight,
  clearSourceResolutionCache,
} from '../skill/scripts/live/generation-preflight.mjs';

const SCRIPTS_DIR = path.resolve('skill/scripts');

test('builds a replace preflight from the picker locator', () => {
  const command = buildGenerationPreflight({
    type: 'generate',
    id: 'session-1',
    count: 3,
    pageUrl: '/pricing',
    element: {
      id: 'hero',
      classes: ['hero', 'hero--dark'],
      tagName: 'SECTION',
      textContent: 'A faster way to ship',
    },
  }, SCRIPTS_DIR);

  assert.equal(command.mode, 'replace');
  assert.deepEqual(command.args.slice(1), [
    '--id', 'session-1', '--count', '3',
    '--defer-source-write',
    '--element-id', 'hero',
    '--classes', 'hero hero--dark',
    '--tag', 'SECTION',
    '--text', 'A faster way to ship',
    '--page-url', '/pricing',
  ]);
});

test('builds an insert preflight from the anchor locator', () => {
  const command = buildGenerationPreflight({
    type: 'generate',
    id: 'session-2',
    count: 2,
    mode: 'insert',
    insert: {
      position: 'before',
      anchor: { classes: ['card'], tagName: 'ARTICLE', textContent: 'Plan' },
    },
  }, SCRIPTS_DIR);

  assert.equal(command.mode, 'insert');
  assert.deepEqual(command.args.slice(1), [
    '--id', 'session-2', '--count', '2',
    '--defer-source-write', '--position', 'before',
    '--classes', 'card', '--tag', 'ARTICLE', '--text', 'Plan',
  ]);
});

test('replace preflight always requests a deferred source write', () => {
  const command = buildGenerationPreflight({
    type: 'generate',
    id: 'session-defer',
    count: 3,
    element: { classes: ['hero'] },
  }, SCRIPTS_DIR);
  assert.ok(command.args.includes('--defer-source-write'));
});

test('returns scaffold metadata without exposing child-process details', async () => {
  const calls = [];
  const result = await runGenerationPreflight({
    type: 'generate',
    id: 'session-3',
    count: 1,
    element: { classes: ['hero'] },
  }, {
    scriptsDir: SCRIPTS_DIR,
    cwd: '/tmp/example',
    async execFileImpl(file, args, options) {
      calls.push({ file, args, options });
      return { stdout: '{"file":"src/App.jsx","insertLine":12}\n', stderr: '' };
    },
  });

  assert.equal(result.ok, true);
  assert.deepEqual(result.scaffold, { file: 'src/App.jsx', insertLine: 12 });
  assert.equal(calls[0].file, process.execPath);
  assert.equal(calls[0].options.cwd, '/tmp/example');
});

test('skips preflight when the picker has no source locator', async () => {
  const result = await runGenerationPreflight({
    type: 'generate',
    id: 'session-4',
    count: 3,
    element: { tagName: 'DIV' },
  }, { scriptsDir: SCRIPTS_DIR });

  assert.deepEqual(result, { ok: false, skipped: true, reason: 'insufficient_locator' });
});

test('yields to the event loop instead of blocking on the child process', async () => {
  // The server is single-threaded and leases polls through this call. A
  // synchronous spawn froze every other request (Accept, Discard, SSE) for the
  // scaffold's full duration — measured at ~7.6s on a large repo.
  let tickedDuringPreflight = false;
  const pending = runGenerationPreflight({
    type: 'generate',
    id: 'session-async',
    count: 1,
    element: { classes: ['hero'] },
  }, {
    scriptsDir: SCRIPTS_DIR,
    execFileImpl: () => new Promise((resolve) => {
      setTimeout(() => resolve({ stdout: '{"file":"src/App.jsx"}\n', stderr: '' }), 25);
    }),
  });
  setTimeout(() => { tickedDuringPreflight = true; }, 5);
  const result = await pending;
  assert.equal(result.ok, true);
  assert.equal(tickedDuringPreflight, true, 'the event loop must stay responsive during preflight');
});

test('caches the resolved source file and reuses it via --file on the next generate', async () => {
  clearSourceResolutionCache();
  const cache = new Map();
  const event = {
    type: 'generate',
    id: 'sess-a',
    count: 3,
    pageUrl: '/pricing',
    element: { classes: ['hero'], tagName: 'SECTION' },
  };
  const firstArgs = [];
  const first = await runGenerationPreflight(event, {
    scriptsDir: SCRIPTS_DIR,
    cache,
    async execFileImpl(_file, args) {
      firstArgs.push(...args);
      return { stdout: '{"file":"src/Pricing.jsx","sourceWritten":false}\n', stderr: '' };
    },
  });
  assert.equal(first.ok, true);
  assert.ok(!firstArgs.includes('--file'), 'first pass does the tree search, no --file');

  // Second generate on the SAME target (new session id) should point --file at
  // the cached resolution and skip the search.
  const secondArgs = [];
  const second = await runGenerationPreflight({ ...event, id: 'sess-b' }, {
    scriptsDir: SCRIPTS_DIR,
    cache,
    async execFileImpl(_file, args) {
      secondArgs.push(...args);
      return { stdout: '{"file":"src/Pricing.jsx","sourceWritten":false}\n', stderr: '' };
    },
  });
  assert.equal(second.ok, true);
  const fileIdx = secondArgs.indexOf('--file');
  assert.notEqual(fileIdx, -1, 'cached resolution injects --file');
  assert.equal(secondArgs[fileIdx + 1], 'src/Pricing.jsx');
});

test('evicts the cached resolution when the preflight fails', async () => {
  const cache = new Map();
  const event = {
    type: 'generate',
    id: 'sess-c',
    count: 3,
    pageUrl: '/pricing',
    element: { classes: ['hero'] },
  };
  await runGenerationPreflight(event, {
    scriptsDir: SCRIPTS_DIR,
    cache,
    async execFileImpl() { return { stdout: '{"file":"src/Pricing.jsx"}\n', stderr: '' }; },
  });
  assert.equal(cache.size, 1);

  const error = new Error('spawn failed');
  error.stderr = 'live-wrap.mjs: element not found\n';
  await runGenerationPreflight(event, {
    scriptsDir: SCRIPTS_DIR,
    cache,
    execFileImpl: () => Promise.reject(error),
  });
  assert.equal(cache.size, 0, 'a failed resolution is evicted so the next run re-searches');
});

test('caches the route source file, not the svelte-component manifest', async () => {
  const cache = new Map();
  const event = {
    type: 'generate',
    id: 'sess-svelte',
    count: 3,
    pageUrl: '/',
    element: { classes: ['hero'] },
  };
  await runGenerationPreflight(event, {
    scriptsDir: SCRIPTS_DIR,
    cache,
    async execFileImpl() {
      return {
        stdout: '{"file":"node_modules/.impeccable-live/x/manifest.json","sourceFile":"src/routes/+page.svelte","previewMode":"svelte-component"}\n',
        stderr: '',
      };
    },
  });
  assert.deepEqual([...cache.values()], ['src/routes/+page.svelte']);
});

test('reports a child-process failure without leaking internals or throwing', async () => {
  const error = new Error('spawn failed');
  error.stderr = 'live-wrap.mjs: element not found\n';
  const result = await runGenerationPreflight({
    type: 'generate',
    id: 'session-fail',
    count: 1,
    element: { classes: ['hero'] },
  }, {
    scriptsDir: SCRIPTS_DIR,
    execFileImpl: () => Promise.reject(error),
  });
  assert.equal(result.ok, false);
  assert.equal(result.error, 'live-wrap.mjs: element not found');
  assert.ok(typeof result.durationMs === 'number');
});
