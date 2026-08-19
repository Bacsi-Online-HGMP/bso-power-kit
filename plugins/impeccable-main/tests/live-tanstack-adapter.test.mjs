/**
 * Unit tests for the TanStack Start live-mode adapter.
 * Run with: node --test tests/live-tanstack-adapter.test.mjs
 */

import { describe, it, beforeEach, afterEach } from 'node:test';
import assert from 'node:assert/strict';
import { existsSync, mkdirSync, mkdtempSync, readFileSync, rmSync, writeFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { tmpdir } from 'node:os';
import { fileURLToPath } from 'node:url';

import {
  detectTanStackStartProject,
  applyTanStackLiveAdapter,
  removeTanStackLiveAdapter,
  patchTanStackRoot,
  unpatchTanStackRoot,
  buildTanStackLiveRootComponent,
} from '../skill/scripts/live/tanstack-adapter.mjs';

const __dirname = dirname(fileURLToPath(import.meta.url));

const ROOT_TSX = `import { HeadContent, Scripts, createRootRoute } from '@tanstack/react-router';

export const Route = createRootRoute({
  shellComponent: RootDocument,
});

function RootDocument({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <head>
        <HeadContent />
      </head>
      <body>
        {children}
        <Scripts />
      </body>
    </html>
  );
}
`;

function scaffold(tmp, { ext = 'tsx', rootBody = ROOT_TSX, startPackage = '@tanstack/react-start' } = {}) {
  mkdirSync(join(tmp, 'src', 'routes'), { recursive: true });
  writeFileSync(join(tmp, 'package.json'), JSON.stringify({
    name: 'app',
    dependencies: { '@tanstack/react-router': '^1', [startPackage]: '^1' },
  }));
  writeFileSync(join(tmp, 'src', 'routes', `__root.${ext}`), rootBody);
}

describe('tanstack-adapter — detection', () => {
  let tmp;
  beforeEach(() => { tmp = mkdtempSync(join(tmpdir(), 'impeccable-tanstack-')); });
  afterEach(() => { rmSync(tmp, { recursive: true, force: true }); });

  it('detects a TanStack Start project from package + root route', () => {
    scaffold(tmp);
    const project = detectTanStackStartProject(tmp);
    assert.equal(project.rootRoute, 'src/routes/__root.tsx');
    assert.equal(project.componentFile, 'src/impeccable/ImpeccableLiveRoot.tsx');
    assert.equal(project.componentImport, '../impeccable/ImpeccableLiveRoot');
  });

  it('mirrors the root-route extension for the mount component (jsx)', () => {
    scaffold(tmp, { ext: 'jsx' });
    const project = detectTanStackStartProject(tmp);
    assert.equal(project.rootRoute, 'src/routes/__root.jsx');
    assert.equal(project.componentFile, 'src/impeccable/ImpeccableLiveRoot.jsx');
  });

  it('detects @tanstack/solid-start and @tanstack/start too', () => {
    scaffold(tmp, { startPackage: '@tanstack/solid-start' });
    assert.ok(detectTanStackStartProject(tmp));
  });

  it('returns null without the Start package (plain TanStack Router SPA)', () => {
    mkdirSync(join(tmp, 'src', 'routes'), { recursive: true });
    writeFileSync(join(tmp, 'package.json'), JSON.stringify({
      dependencies: { '@tanstack/react-router': '^1' },
    }));
    writeFileSync(join(tmp, 'src', 'routes', '__root.tsx'), ROOT_TSX);
    assert.equal(detectTanStackStartProject(tmp), null);
  });

  it('returns null without a root route file', () => {
    writeFileSync(join(tmp, 'package.json'), JSON.stringify({
      dependencies: { '@tanstack/react-start': '^1' },
    }));
    assert.equal(detectTanStackStartProject(tmp), null);
  });
});

describe('tanstack-adapter — patch/unpatch round-trip', () => {
  it('inserts the import + mount component before <Scripts />', () => {
    const patched = patchTanStackRoot(ROOT_TSX, '../impeccable/ImpeccableLiveRoot');
    assert.match(patched, /import ImpeccableLiveRoot from '\.\.\/impeccable\/ImpeccableLiveRoot';/);
    assert.match(patched, /\{\/\* impeccable-live-tanstack-start \*\/\}/);
    assert.match(patched, /<ImpeccableLiveRoot \/>/);
    // component renders before <Scripts />
    assert.ok(patched.indexOf('<ImpeccableLiveRoot />') < patched.indexOf('<Scripts />'));
  });

  it('round-trips byte-for-byte (patch then unpatch)', () => {
    const patched = patchTanStackRoot(ROOT_TSX, '../impeccable/ImpeccableLiveRoot');
    assert.notEqual(patched, ROOT_TSX);
    assert.equal(unpatchTanStackRoot(patched), ROOT_TSX);
  });

  it('is idempotent (double patch adds one import + one mount)', () => {
    const once = patchTanStackRoot(ROOT_TSX, '../impeccable/ImpeccableLiveRoot');
    const twice = patchTanStackRoot(once, '../impeccable/ImpeccableLiveRoot');
    assert.equal(twice, once);
    assert.equal((twice.match(/<ImpeccableLiveRoot \/>/g) || []).length, 1);
    assert.equal((twice.match(/^import ImpeccableLiveRoot/gm) || []).length, 1);
  });

  it('falls back to </body> when <Scripts /> is absent', () => {
    const noScripts = ROOT_TSX.replace(/\s*<Scripts \/>/, '');
    const patched = patchTanStackRoot(noScripts, '../impeccable/ImpeccableLiveRoot');
    assert.match(patched, /<ImpeccableLiveRoot \/>/);
    assert.ok(patched.indexOf('<ImpeccableLiveRoot />') < patched.indexOf('</body>'));
    assert.equal(unpatchTanStackRoot(patched), noScripts);
  });

  it('builds a client-only mount component carrying the token', () => {
    const body = buildTanStackLiveRootComponent(8123, 'tok-xyz');
    assert.match(body, /http:\/\/localhost:8123\/live\.js\?token=tok-xyz/);
    assert.match(body, /useEffect/);
    assert.match(body, /typeof document === 'undefined'/);
    assert.match(body, /data-impeccable-live-tanstack/);
  });
});

describe('tanstack-adapter — apply/remove on disk', () => {
  let tmp;
  beforeEach(() => { tmp = mkdtempSync(join(tmpdir(), 'impeccable-tanstack-')); });
  afterEach(() => { rmSync(tmp, { recursive: true, force: true }); });

  it('apply writes the component + patches root, remove restores byte-for-byte', () => {
    scaffold(tmp);
    const original = readFileSync(join(tmp, 'src/routes/__root.tsx'), 'utf-8');

    const applied = applyTanStackLiveAdapter({ cwd: tmp, port: 9100, token: 'T1' });
    assert.equal(applied.adapter, 'tanstack-start');
    assert.equal(applied.inserted, true);
    assert.ok(existsSync(join(tmp, 'src/impeccable/ImpeccableLiveRoot.tsx')));
    assert.match(readFileSync(join(tmp, 'src/routes/__root.tsx'), 'utf-8'), /ImpeccableLiveRoot/);
    assert.match(
      readFileSync(join(tmp, 'src/impeccable/ImpeccableLiveRoot.tsx'), 'utf-8'),
      /localhost:9100\/live\.js\?token=T1/,
    );

    const removed = removeTanStackLiveAdapter({ cwd: tmp });
    assert.equal(removed.removed, true);
    assert.equal(existsSync(join(tmp, 'src/impeccable/ImpeccableLiveRoot.tsx')), false);
    assert.equal(existsSync(join(tmp, 'src/impeccable')), false, 'empty managed dir pruned');
    assert.equal(readFileSync(join(tmp, 'src/routes/__root.tsx'), 'utf-8'), original);
  });

  it('refuses to clobber an unmanaged file at the component path', () => {
    scaffold(tmp);
    mkdirSync(join(tmp, 'src/impeccable'), { recursive: true });
    writeFileSync(join(tmp, 'src/impeccable/ImpeccableLiveRoot.tsx'), 'export const mine = 1;\n');
    const result = applyTanStackLiveAdapter({ cwd: tmp, port: 9100, token: 'T1' });
    assert.equal(result.error, 'tanstack_component_conflict');
    // unmanaged file untouched
    assert.equal(
      readFileSync(join(tmp, 'src/impeccable/ImpeccableLiveRoot.tsx'), 'utf-8'),
      'export const mine = 1;\n',
    );
  });
});
