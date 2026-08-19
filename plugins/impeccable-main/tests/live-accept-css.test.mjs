import { describe, it } from 'node:test';
import assert from 'node:assert/strict';
import { compile } from 'svelte/compiler';
import {
  bakeParamValues,
  collectAllSelectors,
  normalizeSelector,
  parseStylesheet,
  pruneUnusedSelectors,
  reconcileCss,
  serializeNodes,
  splitSelectorList,
  stripParamSelector,
  substituteParamVar,
} from '../skill/scripts/live/accept-css.mjs';
import { verifyAcceptedSource } from '../skill/scripts/live/accept-verify.mjs';

describe('accept-time CSS reconciliation', () => {
  it('parses rules, at-blocks, and comments with stable round-trip', () => {
    const css = `/* note */\n.a { color: red; }\n@media (min-width: 600px) {\n  .a { color: blue; }\n  .b { margin: 0; }\n}\n@font-face { font-family: X; src: url("a{b}.woff"); }`;
    const nodes = parseStylesheet(css);
    assert.deepEqual(nodes.map((n) => n.type), ['comment', 'rule', 'at', 'at']);
    assert.equal(nodes[2].children.length, 2);
    const out = serializeNodes(nodes);
    assert.match(out, /@media \(min-width: 600px\)/);
    assert.match(out, /a\{b\}\.woff/);
  });

  it('replaces matching selectors instead of appending duplicates', () => {
    const existing = `.pit-board { border-top: 1px solid #333; padding: 8px; }\n.pit-board .label { color: gray; }`;
    const variant = `.pit-board { padding: 12px; clip-path: polygon(0 0); }\n.pit-board .arrow { width: 10px; }`;
    const { css, replaced, appended } = reconcileCss(existing, variant);
    assert.equal(replaced, 1);
    assert.equal(appended, 1);
    // The superseded divider border is gone; the new body wins.
    assert.doesNotMatch(css, /border-top/);
    assert.match(css, /clip-path/);
    assert.match(css, /\.pit-board \.label/);
    assert.match(css, /\.pit-board \.arrow/);
    // Exactly one .pit-board rule remains.
    assert.equal(css.split('.pit-board {').length - 1, 1);
  });

  it('merges inside matching media queries', () => {
    const existing = `@media (max-width: 700px) { .row { gap: 4px; } }`;
    const variant = `@media (max-width: 700px) { .row { gap: 8px; } .col { gap: 2px; } }`;
    const { css } = reconcileCss(existing, variant);
    assert.match(css, /gap: 8px/);
    assert.doesNotMatch(css, /gap: 4px/);
    assert.match(css, /\.col \{ gap: 2px; \}/);
    assert.equal(css.split('@media').length - 1, 1);
  });

  it('normalizes selectors for matching', () => {
    assert.equal(normalizeSelector('.a  >  .b,  .c'), '.a>.b,.c');
    assert.deepEqual(splitSelectorList('.a[data-x="1,2"], .b:is(.c, .d)'), ['.a[data-x="1,2"]', '.b:is(.c, .d)']);
  });
});

describe('param baking', () => {
  it('substitutes range vars with paren-aware fallbacks', () => {
    const css = `.x { width: calc(var(--p-depth, calc(2px * 3)) + 1px); opacity: var(--p-depth); }`;
    const out = substituteParamVar(css, 'depth', '10px');
    assert.equal(out, `.x { width: calc(10px + 1px); opacity: 10px; }`);
  });

  it('keeps only the chosen steps branch and strips the attribute selector', () => {
    const css = [
      `:global([data-p-density="airy"]) .grid { gap: 24px; }`,
      `:global([data-p-density="snug"]) .grid { gap: 8px; }`,
      `.grid { display: grid; }`,
    ].join('\n');
    const out = bakeParamValues(css, [
      { id: 'density', kind: 'steps', default: 'airy' },
    ], { density: 'snug' });
    assert.doesNotMatch(out, /24px/);
    assert.doesNotMatch(out, /data-p-density/);
    assert.match(out, /\.grid \{ gap: 8px; \}/);
    assert.match(out, /\.grid \{ display: grid; \}/);
  });

  it('normalizes toggle booleans to 0/1 and resolves presence selectors', () => {
    const css = `.t { opacity: var(--p-serif, 0); }\n[data-p-serif] .t { font-family: serif; }`;
    const on = bakeParamValues(css, [{ id: 'serif', kind: 'toggle', default: false }], { serif: true });
    assert.match(on, /opacity: 1/);
    assert.match(on, /\.t \{ font-family: serif; \}/);
    const off = bakeParamValues(css, [{ id: 'serif', kind: 'toggle', default: false }], { serif: false });
    assert.match(off, /opacity: 0/);
    assert.doesNotMatch(off, /font-family: serif/);
  });

  it('falls back to declared defaults when no value was sent', () => {
    const css = `.x { gap: var(--p-gap, 4px); }`;
    const out = bakeParamValues(css, [{ id: 'gap', kind: 'range', default: 12 }], {});
    assert.match(out, /gap: 12/);
  });

  it('bakes undeclared sent values as ranges instead of ignoring them', () => {
    const css = `.x { gap: var(--p-mystery, 4px); }`;
    const out = bakeParamValues(css, [], { mystery: '9px' });
    assert.match(out, /gap: 9px/);
  });

  it('drops rules whose bodies become empty and strips readiness sentinels', () => {
    const css = `.x { --impeccable-variant-ready: 1; }\n.y { color: red; }`;
    const out = bakeParamValues(css, [], {});
    assert.doesNotMatch(out, /impeccable-variant-ready/);
    assert.doesNotMatch(out, /\.x/);
    assert.match(out, /\.y/);
  });

  it('stripParamSelector cleans emptied :global wrappers', () => {
    assert.equal(stripParamSelector(':global([data-p-a="x"]) .b', 'a', 'steps', 'x'), '.b');
    assert.equal(stripParamSelector(':global([data-p-a="x"]) .b', 'a', 'steps', 'y'), null);
    assert.equal(stripParamSelector('.root[data-p-flag] .b', 'flag', 'toggle', true), '.root .b');
    assert.equal(stripParamSelector('.root[data-p-flag] .b', 'flag', 'toggle', false), null);
  });
});

describe('compiler-driven pruning', () => {
  it('removes selectors svelte reports as unused', () => {
    const component = `<div class="kept"><span class="inner">hi</span></div>\n<style>\n  .kept { color: red; }\n  .gone { color: blue; }\n  .kept .inner, .kept .missing { font-weight: bold; }\n  @media (min-width: 600px) { .alsogone { padding: 4px; } .kept { margin: 0; } }\n</style>`;
    const { source, removed } = pruneUnusedSelectors(component, compile);
    assert.equal(removed.includes('.gone'), true);
    assert.equal(removed.includes('.alsogone'), true);
    assert.doesNotMatch(source, /color: blue/);
    assert.doesNotMatch(source, /\.alsogone/);
    assert.match(source, /\.kept \{ color: red; \}/);
    assert.match(source, /\.kept \.inner \{ font-weight: bold; \}/);
    assert.match(source, /\.kept \{ margin: 0; \}/);
    // The pruned result still compiles without unused-selector warnings.
    const { warnings } = compile(source, { generate: false });
    assert.deepEqual(warnings.filter((w) => w.code === 'css_unused_selector'), []);
  });

  it('never throws on uncompilable input', () => {
    const { source } = pruneUnusedSelectors('<div>{broken', () => { throw new Error('nope'); });
    assert.equal(source, '<div>{broken');
  });

  it('prunes past child combinators without truncating the selector list', () => {
    // The prelude walk must not treat the child combinator as a boundary:
    // cutting at the `>` of `.wrap > .item` used to rewrite the list from
    // mid-prelude.
    const component = `<div class="wrap"><p class="item">x</p></div>\n<style>\n  .wrap > .item, .orphan { font-weight: bold; }\n  .wrap { padding: 4px; }\n</style>`;
    const { source, removed } = pruneUnusedSelectors(component, compile);
    assert.deepEqual(removed, ['.orphan']);
    assert.match(source, /\.wrap > \.item \{ font-weight: bold; \}/);
    assert.match(source, /\.wrap \{ padding: 4px; \}/);
    const { warnings } = compile(source, { generate: false });
    assert.deepEqual(warnings.filter((w) => w.code === 'css_unused_selector'), []);
  });

  it('removes a fully unused combinator rule without leaving a dangling fragment', () => {
    // The corruption shape: after a mid-prelude cut, every remaining fragment
    // equals the flagged selector, so the whole-rule branch deleted from the
    // cut point and left `.wrap >` dangling in source.
    const component = `<div class="wrap"><p class="item">x</p></div>\n<style>\n  .wrap > .orphan, .orphan { color: blue; }\n  .wrap { padding: 4px; }\n</style>`;
    const { source } = pruneUnusedSelectors(component, compile);
    assert.doesNotMatch(source, /\.orphan/);
    assert.doesNotMatch(source, /\.wrap >\s*\{/, 'no dangling combinator fragment');
    assert.doesNotMatch(source, /\.wrap >\s*$/m, 'no dangling combinator line');
    assert.match(source, /\.wrap \{ padding: 4px; \}/);
    const { warnings } = compile(source, { generate: false });
    assert.deepEqual(warnings.filter((w) => w.code === 'css_unused_selector'), []);
  });
});

describe('postcondition scanner', () => {
  it('flags every class of live-mode leftover with line numbers', () => {
    const dirty = [
      '<div data-impeccable-variant="2">x</div>',
      '<!-- impeccable-param-values abc: {"d":1} -->',
      '.x { width: var(--p-depth, 4px); }',
      '<section data-p-density="snug">y</section>',
      '<!-- impeccable-carbonize-start abc -->',
    ].join('\n');
    const { clean, findings } = verifyAcceptedSource(dirty);
    assert.equal(clean, false);
    assert.equal(findings.length >= 5, true);
    assert.deepEqual(findings.map((f) => f.line).slice(0, 5), [1, 2, 3, 4, 5]);
  });

  it('passes clean source', () => {
    const { clean } = verifyAcceptedSource('<div class="pit-board">ok</div>\n<style>.pit-board { gap: 8px; }</style>');
    assert.equal(clean, true);
  });
});

describe('review regressions: parser boundaries', () => {
  it('parses compact CSS with no whitespace between rules (B1)', () => {
    const nodes = parseStylesheet('.a{x:1}.b{y:2}.c{z:3}');
    assert.deepEqual(nodes.map((n) => n.prelude), ['.a', '.b', '.c']);
  });

  it('accept-style reconcile survives a minified existing block (B1)', () => {
    const { css } = reconcileCss('.pit-board{display:flex}.stage{padding:8px}.footer{color:gray}', '.pit-board { display: grid; }');
    assert.match(css, /\.stage \{ padding:8px \}/);
    assert.match(css, /\.footer \{ color:gray \}/);
    assert.match(css, /display: grid/);
    assert.doesNotMatch(css, /display:flex/);
  });

  it('block-less at-statements do not swallow the following rule (M4)', () => {
    const existing = '@import url("t.css");\n.a { color: red; border: 1px solid black; }\n.b { z-index: 1; }';
    const { css, replaced } = reconcileCss(existing, '.a { color: green; }');
    assert.equal(replaced, 1);
    assert.doesNotMatch(css, /border: 1px solid black/);
    assert.match(css, /color: green/);
    assert.match(css, /@import url\("t\.css"\);/);
    assert.match(css, /\.b \{ z-index: 1; \}/);
    assert.equal(css.split('.a {').length - 1, 1);
  });

  it('keeps sibling declarations when stripping a one-line sentinel (m1)', () => {
    const out = bakeParamValues('.x { --impeccable-variant-ready: 1; color: red; padding: 4px; }', [], {});
    assert.match(out, /color: red/);
    assert.match(out, /padding: 4px/);
    assert.doesNotMatch(out, /impeccable-variant-ready/);
  });

  it('collectAllSelectors sees rules at every nesting level', () => {
    const selectors = collectAllSelectors('.a { x: 1; }\n@media (min-width: 10px) { .b { y: 2; } @supports (display: grid) { .c { z: 3; } } }');
    assert.deepEqual([...selectors].sort(), ['.a', '.b', '.c']);
  });
});

describe('review regressions: toggle branch truth', () => {
  it('drops valued toggle branches that never matched at preview, keeps on-forms only while on', () => {
    assert.equal(stripParamSelector('[data-p-flag="false"] .a', 'flag', 'toggle', true), null);
    assert.equal(stripParamSelector('[data-p-flag="false"] .a', 'flag', 'toggle', false), null);
    assert.equal(stripParamSelector('[data-p-flag="0"] .a', 'flag', 'toggle', false), null);
    assert.equal(stripParamSelector('[data-p-flag="on"] .a', 'flag', 'toggle', true), '.a');
    assert.equal(stripParamSelector('[data-p-flag="on"] .a', 'flag', 'toggle', false), null);
    assert.equal(stripParamSelector('[data-p-flag] .a', 'flag', 'toggle', true), '.a');
    assert.equal(stripParamSelector('[data-p-flag] .a', 'flag', 'toggle', false), null);
  });
});

describe('review regressions: verify precision', () => {
  it('does not flag user tokens that merely share the p- prefix', () => {
    const clean = [
      '<div data-page="3" data-p-count-like data-photo="x">ok</div>',
      '.a { color: var(--primary); padding: var(--padding, 4px); }',
    ].join('\n');
    assert.equal(verifyAcceptedSource(clean).clean, true, JSON.stringify(verifyAcceptedSource(clean).findings));
  });

  it('still flags the exact shapes live mode writes', () => {
    const dirty = [
      '<div data-p-density="snug">x</div>',
      '.a { gap: var(--p-depth, 4px); }',
      '.b[data-p-flag] { color: red; }',
    ].join('\n');
    const { clean, findings } = verifyAcceptedSource(dirty);
    assert.equal(clean, false);
    assert.equal(findings.length >= 3, true);
  });
});
