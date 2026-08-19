/**
 * Conformance tests for the live-mode framework registry.
 *
 * Two jobs:
 *
 *   1. Every entry in FRAMEWORKS satisfies the contract the live scripts rely
 *      on — a callable detect, a resolvable inject strategy, source traits
 *      drawn from the closed sets, and undo functions for every patch kind it
 *      can journal. A new framework module that forgets a field fails here
 *      rather than at a user's inject.
 *   2. detect() lands on the expected entry for the static framework fixtures.
 *      This is the seed of the conformance battery; behavioral conformance
 *      (does the injected bundle actually boot in that framework) stays in the
 *      live-e2e suite. Fixtures are read-only here.
 *
 * Plus the crash-safe injection journal, which is registry-layer code: it
 * heals through the entries' own undo functions.
 *
 * Run with: node --test tests/live-frameworks.test.mjs
 */

import { describe, it, beforeEach, afterEach } from 'node:test';
import assert from 'node:assert/strict';
import { existsSync, mkdirSync, mkdtempSync, readFileSync, rmSync, writeFileSync } from 'node:fs';
import { dirname, join, resolve } from 'node:path';
import { tmpdir } from 'node:os';
import { fileURLToPath } from 'node:url';

import {
  COMMENT_SYNTAXES,
  FRAMEWORKS,
  INJECT_KINDS,
  PATCH_UNDOERS,
  PREVIEW_MODES,
  SOURCE_TRAIT_DEFAULTS,
  STYLE_MODES,
  TAG_PATCH_KIND,
  describeInjectArtifacts,
  frameworkIgnorePatterns,
  resolveFramework,
  resolveSourceTraits,
} from '../skill/scripts/live/frameworks/index.mjs';
import {
  clearInjectJournal,
  healInjectJournal,
  injectJournalPath,
  readInjectJournal,
  recordInjection,
} from '../skill/scripts/live/frameworks/journal.mjs';
import { insertTag } from '../skill/scripts/live/frameworks/tag-strategy.mjs';

const __dirname = dirname(fileURLToPath(import.meta.url));
const FIXTURES_DIR = join(__dirname, 'framework-fixtures');

/** Read-only: the fixture's project tree plus its live config. */
function fixtureProject(name) {
  const root = join(FIXTURES_DIR, name, 'files');
  const manifest = join(FIXTURES_DIR, name, 'fixture.json');
  if (!existsSync(root) || !existsSync(manifest)) return null;
  return { root, config: JSON.parse(readFileSync(manifest, 'utf-8')).config };
}

// ---------------------------------------------------------------------------
// Contract shape
// ---------------------------------------------------------------------------

describe('framework registry — entry contract', () => {
  it('declares the documented detection priority, terminating in static-html', () => {
    assert.deepEqual(
      FRAMEWORKS.map((f) => f.name),
      ['sveltekit', 'nuxt', 'tanstack-start', 'astro', 'nextjs', 'vite-generic', 'static-html'],
      'detection order is injection priority; live-inject.mjs used to hard-code exactly this',
    );
    assert.equal(FRAMEWORKS.at(-1).name, 'static-html');
    assert.ok(FRAMEWORKS.at(-1).detect(process.cwd(), null), 'the terminal entry must always match');
  });

  it('gives every entry a unique name', () => {
    const names = FRAMEWORKS.map((f) => f.name);
    assert.equal(new Set(names).size, names.length);
    for (const name of names) {
      assert.equal(typeof name, 'string');
      assert.ok(name.length > 0);
    }
  });

  for (const framework of FRAMEWORKS) {
    describe(`entry · ${framework.name}`, () => {
      it('exposes a callable detect', () => {
        assert.equal(typeof framework.detect, 'function');
      });

      it('resolves its inject strategy', () => {
        const { inject } = framework;
        assert.ok(inject, 'entry declares an inject strategy');
        assert.ok(INJECT_KINDS.includes(inject.kind), `unknown inject kind ${inject.kind}`);
        if (inject.kind === 'adapter') {
          assert.equal(typeof inject.apply, 'function');
          assert.equal(typeof inject.remove, 'function');
          assert.equal(typeof inject.artifacts, 'function', 'adapters must declare what they write');
          assert.equal(typeof inject.ignorePatterns, 'function');
        } else {
          // The tag strategy is shared; an entry declaring per-framework
          // apply/remove alongside kind:'tag' would silently never run.
          assert.equal(inject.apply, undefined);
          assert.equal(inject.remove, undefined);
        }
      });

      it('registers an undo for every patch kind it can journal', () => {
        for (const key of Object.keys(framework.inject.unpatch || {})) {
          assert.equal(typeof PATCH_UNDOERS[key], 'function', `no undo registered for ${key}`);
        }
      });

      it('declares source traits from the closed sets', () => {
        const { source } = framework;
        assert.ok(Array.isArray(source.extensions) && source.extensions.length > 0);
        for (const ext of source.extensions) {
          assert.match(ext, /^\.[a-z0-9]+$/, 'extensions are lowercase and dotted');
          const traits = resolveSourceTraits(`Example${ext}`);
          assert.ok(PREVIEW_MODES.includes(traits.preview), `bad preview ${traits.preview}`);
          assert.ok(STYLE_MODES.includes(traits.styleMode), `bad styleMode ${traits.styleMode}`);
          assert.ok(COMMENT_SYNTAXES.includes(traits.commentSyntax), `bad commentSyntax ${traits.commentSyntax}`);
          assert.equal(typeof traits.styleTag, 'string');
          assert.equal(typeof traits.injectScriptAttrs, 'string');
        }
      });
    });
  }

  it('keeps shared extensions in agreement across entries', () => {
    // `.tsx` belongs to tanstack-start, nextjs and vite-generic. resolveSourceTraits
    // returns the first claimant, so a disagreement would resolve by array
    // position instead of by intent.
    const seen = new Map();
    for (const framework of FRAMEWORKS) {
      for (const ext of framework.source.extensions) {
        const traits = { ...SOURCE_TRAIT_DEFAULTS, ...framework.source };
        delete traits.extensions;
        const prior = seen.get(ext);
        if (!prior) { seen.set(ext, { name: framework.name, traits }); continue; }
        assert.deepEqual(
          traits,
          prior.traits,
          `${framework.name} and ${prior.name} both claim ${ext} but disagree on its traits`,
        );
      }
    }
  });

  it('falls back to the defaults for an unclaimed extension', () => {
    const traits = resolveSourceTraits('src/helpers.ts');
    assert.equal(traits.framework, null);
    assert.equal(traits.preview, 'source');
    assert.equal(traits.styleMode, 'scoped');
    assert.equal(traits.commentSyntax, 'html');
    assert.equal(traits.injectScriptAttrs, '');
  });

  it('routes the three authoring modes live-wrap depends on', () => {
    assert.equal(resolveSourceTraits('src/routes/+page.svelte').preview, 'component');
    assert.equal(resolveSourceTraits('src/pages/index.astro').styleMode, 'astro-global-prefixed');
    assert.equal(resolveSourceTraits('src/pages/index.astro').injectScriptAttrs, 'is:inline ');
    assert.equal(resolveSourceTraits('app/page.tsx').commentSyntax, 'jsx');
    assert.equal(resolveSourceTraits('index.html').commentSyntax, 'html');
    assert.equal(resolveSourceTraits('app/app.vue').styleMode, 'scoped');
  });

  it('registers the generic tag undo', () => {
    assert.equal(typeof PATCH_UNDOERS[TAG_PATCH_KIND], 'function');
  });
});

// ---------------------------------------------------------------------------
// Detection against the static fixtures (read-only)
// ---------------------------------------------------------------------------

describe('framework registry — fixture detection', () => {
  /**
   * `sveltekit` is deliberately absent: that fixture is a bare src/app.html +
   * one route with no svelte.config and no package.json, and the SvelteKit
   * detector has always required one of those. It resolves to static-html and
   * takes the generic tag path, which is exactly what live-inject did before
   * the registry. `vite8-sveltekit` is the fully-shaped SvelteKit fixture.
   */
  const EXPECTED = {
    'vite8-sveltekit': 'sveltekit',
    'vite8-sveltekit-stateful': 'sveltekit',
    'sveltekit-csp': 'sveltekit',
    'nuxt-vite7': 'nuxt',
    'nuxt-csp': 'nuxt',
    'tanstack-start': 'tanstack-start',
    // A plain TanStack Router SPA has no @tanstack/react-start and a static
    // index.html, so it must NOT take the SSR adapter.
    'tanstack-router-vite': 'vite-generic',
    astro: 'astro',
    'astro-vite7': 'astro',
    'nextjs-app': 'nextjs',
    'nextjs-app-router': 'nextjs',
    'vite8-react-plain': 'vite-generic',
    'vite8-react-ts': 'vite-generic',
    'multipage-with-generator': 'static-html',
  };

  for (const [name, expected] of Object.entries(EXPECTED)) {
    it(`${name} resolves to ${expected}`, (t) => {
      const project = fixtureProject(name);
      if (!project) {
        t.skip(`fixture ${name} is not present`);
        return;
      }
      const resolved = resolveFramework(project.root, project.config);
      assert.ok(resolved, 'a framework always resolves');
      assert.equal(resolved.framework.name, expected);
      assert.ok(resolved.project, 'detect returns a truthy project descriptor');
    });
  }

  it('the bare sveltekit fixture keeps the pre-registry generic path', () => {
    const project = fixtureProject('sveltekit');
    if (!project) return;
    const resolved = resolveFramework(project.root, project.config);
    assert.equal(resolved.framework.name, 'static-html');
    assert.equal(resolved.framework.inject.kind, 'tag');
  });

  it('adapters ask for the gitignore patterns their generated paths need', () => {
    const nuxt = fixtureProject('nuxt-vite7');
    const resolvedNuxt = resolveFramework(nuxt.root, nuxt.config);
    assert.deepEqual(frameworkIgnorePatterns(resolvedNuxt), ['plugins/impeccable-live.client.ts']);

    const tanstack = fixtureProject('tanstack-start');
    const resolvedTanstack = resolveFramework(tanstack.root, tanstack.config);
    assert.deepEqual(
      frameworkIgnorePatterns(resolvedTanstack),
      ['src/impeccable/ImpeccableLiveRoot.tsx'],
    );

    const vite = fixtureProject('vite8-react-plain');
    assert.deepEqual(frameworkIgnorePatterns(resolveFramework(vite.root, vite.config)), []);
  });

  it('describes adapter artifacts as created files plus patched anchors', () => {
    const tanstack = fixtureProject('tanstack-start');
    const resolved = resolveFramework(tanstack.root, tanstack.config);
    const artifacts = describeInjectArtifacts(resolved, { cwd: tanstack.root, files: [] });
    assert.deepEqual(artifacts.map((a) => [a.kind, a.path]), [
      ['created', 'src/impeccable/ImpeccableLiveRoot.tsx'],
      ['patched', 'src/routes/__root.tsx'],
    ]);
    for (const artifact of artifacts) {
      if (artifact.kind === 'patched') {
        assert.equal(typeof PATCH_UNDOERS[artifact.patch], 'function');
        assert.ok(artifact.markers.length > 0, 'patched artifacts carry ownership markers');
      } else {
        assert.ok(artifact.marker, 'created artifacts carry an ownership marker');
      }
    }
  });

  it('describes tag-strategy artifacts as one patch per resolved file', () => {
    const vite = fixtureProject('vite8-react-plain');
    const resolved = resolveFramework(vite.root, vite.config);
    const artifacts = describeInjectArtifacts(resolved, { cwd: vite.root, files: ['index.html', 'other.html'] });
    assert.deepEqual(artifacts.map((a) => a.path), ['index.html', 'other.html']);
    assert.ok(artifacts.every((a) => a.kind === 'patched' && a.patch === TAG_PATCH_KIND));
  });
});

// ---------------------------------------------------------------------------
// Crash-safe injection journal
// ---------------------------------------------------------------------------

const PRISTINE_HTML = '<!DOCTYPE html>\n<html>\n  <body>\n    <h1>Hello</h1>\n  </body>\n</html>\n';
// Exactly what an inject leaves behind, so healing has to restore the original
// bytes the same way `--remove` does.
const INJECTED_HTML = insertTag(
  PRISTINE_HTML,
  { insertBefore: '</body>', commentSyntax: 'html' },
  8400,
  undefined,
  '',
);

const NUXT_PLUGIN_BODY = '/* impeccable-live-nuxt-plugin */\nexport default defineNuxtPlugin(() => {});\n';

describe('inject journal — crash recovery', () => {
  let tmp;
  beforeEach(() => { tmp = mkdtempSync(join(tmpdir(), 'impeccable-journal-')); });
  afterEach(() => { rmSync(tmp, { recursive: true, force: true }); });

  /** Simulate a session that wrote artifacts and was SIGKILLed before stop. */
  function stageKilledSession({ withPlugin = true, withTag = true } = {}) {
    const artifacts = [];
    if (withPlugin) {
      mkdirSync(join(tmp, 'app', 'plugins'), { recursive: true });
      writeFileSync(join(tmp, 'app', 'plugins', 'impeccable-live.client.ts'), NUXT_PLUGIN_BODY);
      artifacts.push({
        kind: 'created',
        path: 'app/plugins/impeccable-live.client.ts',
        marker: 'impeccable-live-nuxt-plugin',
        pruneTo: 'app',
      });
    }
    if (withTag) {
      writeFileSync(join(tmp, 'index.html'), INJECTED_HTML);
      artifacts.push({
        kind: 'patched',
        path: 'index.html',
        patch: TAG_PATCH_KIND,
        markers: ['impeccable-live-start', 'data-impeccable-csp-original'],
      });
    }
    recordInjection(tmp, { framework: 'nuxt', port: 8400, artifacts });
    return artifacts;
  }

  it('writes the journal under .impeccable/live/ so the ignore block covers it', () => {
    stageKilledSession();
    assert.equal(injectJournalPath(tmp), join(tmp, '.impeccable', 'live', 'inject-journal.json'));
    assert.ok(existsSync(injectJournalPath(tmp)));
    const journal = readInjectJournal(tmp);
    assert.equal(journal.version, 1);
    assert.equal(journal.framework, 'nuxt');
    assert.equal(journal.port, 8400);
    assert.equal(journal.appRoot, resolve(tmp));
    assert.equal(journal.artifacts.length, 2);
  });

  it('heals a SIGKILLed session back to a clean tree', () => {
    stageKilledSession();

    const { healed } = healInjectJournal(tmp);

    assert.deepEqual(
      healed.map((h) => [h.path, h.action]).sort(),
      [['app/plugins/impeccable-live.client.ts', 'removed'], ['index.html', 'unpatched']].sort(),
    );
    assert.equal(
      existsSync(join(tmp, 'app', 'plugins', 'impeccable-live.client.ts')),
      false,
      'the generated plugin is gone',
    );
    assert.equal(
      existsSync(join(tmp, 'app', 'plugins')),
      false,
      'the generated plugins/ directory is pruned',
    );
    assert.equal(existsSync(join(tmp, 'app')), true, 'pruning stops at the declared boundary');
    assert.equal(
      readFileSync(join(tmp, 'index.html'), 'utf-8'),
      PRISTINE_HTML,
      'the patched entry is restored byte-for-byte, same as --remove would',
    );
    assert.equal(readInjectJournal(tmp), null, 'a fully healed journal is cleared');
  });

  it('is idempotent — a second heal finds nothing to do', () => {
    stageKilledSession();
    healInjectJournal(tmp);
    const second = healInjectJournal(tmp);
    assert.deepEqual(second.healed, []);
    assert.deepEqual(second.kept, []);
    assert.equal(existsSync(injectJournalPath(tmp)), false);
  });

  it('keeps artifacts the current run is about to rewrite', () => {
    stageKilledSession();

    const { healed, kept } = healInjectJournal(tmp, {
      keep: ['app/plugins/impeccable-live.client.ts'],
    });

    assert.deepEqual(healed.map((h) => h.path), ['index.html']);
    assert.deepEqual(kept.map((k) => k.path), ['app/plugins/impeccable-live.client.ts']);
    assert.ok(
      existsSync(join(tmp, 'app', 'plugins', 'impeccable-live.client.ts')),
      'a kept artifact is left in place so re-injection stays byte-idempotent',
    );
    const journal = readInjectJournal(tmp);
    assert.deepEqual(journal.artifacts.map((a) => a.path), ['app/plugins/impeccable-live.client.ts']);
  });

  it('disowns a generated file the user has since replaced', () => {
    stageKilledSession({ withTag: false });
    const pluginPath = join(tmp, 'app', 'plugins', 'impeccable-live.client.ts');
    const userBody = 'export default defineNuxtPlugin(() => { /* mine now */ });\n';
    writeFileSync(pluginPath, userBody);

    const { healed } = healInjectJournal(tmp);

    assert.deepEqual(healed, [], 'nothing is reported as healed');
    assert.equal(readFileSync(pluginPath, 'utf-8'), userBody, 'the user file survives untouched');
    assert.equal(readInjectJournal(tmp), null, 'but we stop claiming it');
  });

  it('leaves a patched file alone once its markers are gone', () => {
    stageKilledSession({ withPlugin: false });
    // Whitespace an undo function would normalize, with no marker left.
    const handEdited = '<html>\n\n\n  <body>\n  </body>\n</html>\n';
    writeFileSync(join(tmp, 'index.html'), handEdited);

    const { healed } = healInjectJournal(tmp);

    assert.deepEqual(healed, []);
    assert.equal(readFileSync(join(tmp, 'index.html'), 'utf-8'), handEdited);
  });

  it('tolerates artifacts whose files are already gone', () => {
    stageKilledSession({ withTag: false });
    rmSync(join(tmp, 'app', 'plugins', 'impeccable-live.client.ts'));

    const { healed } = healInjectJournal(tmp);

    assert.deepEqual(healed, []);
    assert.equal(existsSync(injectJournalPath(tmp)), false);
  });

  it('no-ops without a journal, and clears cleanly', () => {
    assert.deepEqual(healInjectJournal(tmp), { healed: [], kept: [] });
    clearInjectJournal(tmp);
    assert.equal(readInjectJournal(tmp), null);
  });

  it('drops the journal file when an injection wrote nothing', () => {
    stageKilledSession({ withTag: false });
    recordInjection(tmp, { framework: 'static-html', port: 8400, artifacts: [] });
    assert.equal(existsSync(injectJournalPath(tmp)), false);
  });
});

describe('sveltekit adapter: token revision and byte-exact removal', () => {
  let adapter;
  beforeEach(async () => {
    adapter = await import('../skill/scripts/live/sveltekit-adapter.mjs');
  });

  const LAYOUT = `<script>
  import '../app.css';

  let { children } = $props();
</script>

{@render children()}
`;

  it('stamps the import with a token-derived revision and swaps it on rotation', () => {
    const revA = adapter.svelteAdapterRev('token-a');
    const revB = adapter.svelteAdapterRev('token-b');
    assert.match(revA, /^[0-9a-f]{8}$/);
    assert.notEqual(revA, revB, 'a rotated token must change the module specifier');

    const patchedA = adapter.patchSvelteLayout(LAYOUT, { rev: revA });
    assert.ok(patchedA.includes(`ImpeccableLiveRoot.svelte?impeccable-live=${revA}'`), 'import carries the revision');

    // A re-apply after helper restart replaces the import IN PLACE: exactly
    // one import, at the new revision, same indentation. A stale specifier
    // is a cached module with a rotated-out token, which 401s on live.js.
    const patchedB = adapter.patchSvelteLayout(patchedA, { rev: revB });
    const importCount = (patchedB.match(/import ImpeccableLiveRoot/g) || []).length;
    assert.equal(importCount, 1, 'rotation must not stack imports');
    assert.ok(patchedB.includes(`?impeccable-live=${revB}'`));
    assert.ok(!patchedB.includes(`?impeccable-live=${revA}'`));
    assert.match(patchedB, /\n  import ImpeccableLiveRoot/, 'replacement keeps the original indentation');
  });

  it('removal restores the layout byte-for-byte, including neighbor indentation', () => {
    // The field failure: the old removal regex used \s* and swallowed the
    // NEXT line's indentation, de-indenting the user's stylesheet import.
    for (const rev of [null, adapter.svelteAdapterRev('some-token')]) {
      const patched = adapter.patchSvelteLayout(LAYOUT, { rev });
      assert.notEqual(patched, LAYOUT, 'patch must change the layout');
      const restored = adapter.unpatchSvelteLayout(patched);
      assert.equal(restored, LAYOUT, `removal must be byte-exact (rev=${rev})`);
    }
  });

  it('removal of a created-from-scratch layout leaves no script husk', () => {
    const patched = adapter.patchSvelteLayout('', { rev: adapter.svelteAdapterRev('t') });
    const restored = adapter.unpatchSvelteLayout(patched);
    assert.doesNotMatch(restored, /ImpeccableLiveRoot|impeccable-live-svelte/);
    assert.doesNotMatch(restored, /<script>\s*<\/script>/);
  });

  it('the root component embeds the tokened URL and reports load failures', () => {
    const body = adapter.buildSvelteLiveRootComponent(4321, 'tok123');
    assert.match(body, /live\.js\?token=tok123/);
    assert.match(body, /onerror/, 'a stale-token 401 must be diagnosable from the console');
  });
});
