import { describe, it } from 'node:test';
import assert from 'node:assert/strict';
import { parse, compile } from 'svelte/compiler';
import {
  analyzeSvelteMarkup,
  buildPropsScriptV2,
  collectRootIdentifiers,
  derivePropName,
  restoreSvelteMarkup,
} from '../skill/scripts/live/svelte-ast.mjs';

const PIT_BOARD = `<ol class="stages" data-active={activeId}>
  {#each stages as stage, i}
    <li class="stage">
      <span class="label">{stage.label}</span>
      <p class="detail">{stage.detail}</p>
      {#if stage.active}<span class="dot"></span>{/if}
    </li>
  {/each}
  <p class="footer">{footerNote}</p>
</ol>`;

describe('svelte AST scaffolding', () => {
  it('turns a free each collection into one structured prop and keeps the loop intact', () => {
    const res = analyzeSvelteMarkup(PIT_BOARD, parse);
    assert.equal(res.ok, true, res.reason);
    const collection = res.contract.find((c) => c.kind === 'collection');
    assert.equal(collection.prop, 'stages');
    assert.equal(collection.expr, 'stages');
    // The loop body survives verbatim: bound expressions are not props.
    assert.match(res.markupWithProps, /\{#each stages as stage, i\}/);
    assert.match(res.markupWithProps, /\{stage\.label\}/);
    assert.match(res.markupWithProps, /\{#if stage\.active\}/);
    // No prop entries for bound expressions.
    assert.equal(res.contract.some((c) => c.expr.includes('stage.')), false);
  });

  it('records the item hydration description for each blocks', () => {
    const res = analyzeSvelteMarkup(PIT_BOARD, parse);
    const collection = res.contract.find((c) => c.kind === 'collection');
    assert.equal(collection.item.rootTag, 'li');
    assert.deepEqual(collection.item.rootClasses, ['stage']);
    assert.deepEqual(collection.item.textSlots.map((s) => s.key), ['label', 'detail']);
  });

  it('extracts free text and attribute expressions as props', () => {
    const res = analyzeSvelteMarkup(PIT_BOARD, parse);
    const props = Object.fromEntries(res.contract.map((c) => [c.expr, c]));
    assert.equal(props['footerNote'].kind, 'text');
    assert.equal(props['activeId'].kind, 'text');
    assert.match(res.markupWithProps, /data-active=\{activeId\}/);
  });

  it('names collection props from member tails and restores them precisely', () => {
    const src = `<ul>{#each data.stages as s}<li>{s.name}</li>{/each}</ul>`;
    const res = analyzeSvelteMarkup(src, parse);
    assert.equal(res.ok, true, res.reason);
    assert.match(res.markupWithProps, /\{#each stages as s\}/);
    const restored = restoreSvelteMarkup(res.markupWithProps, res.contract, parse);
    assert.equal(restored.ok, true);
    assert.equal(restored.markup, src);
  });

  it('classifies event handler expressions as handler props', () => {
    const src = `<button onclick={handleGo} class="go">{label}</button>`;
    const res = analyzeSvelteMarkup(src, parse);
    assert.equal(res.ok, true, res.reason);
    const handler = res.contract.find((c) => c.expr === 'handleGo');
    assert.equal(handler.kind, 'handler');
  });

  it('deduplicates repeated expressions and disambiguates name collisions', () => {
    const src = `<div><h1>{a.title}</h1><h2>{b.title}</h2><p>{a.title}</p></div>`;
    const res = analyzeSvelteMarkup(src, parse);
    assert.equal(res.ok, true, res.reason);
    const names = res.contract.map((c) => c.prop);
    assert.deepEqual(names, ['title', 'title2']);
  });

  it('supports independent nested each blocks but rejects bound nested ones', () => {
    const independent = `<div>{#each rows as r}<p>{r.x}</p>{/each}{#each cols as c}<p>{c.y}</p>{/each}</div>`;
    const okRes = analyzeSvelteMarkup(independent, parse);
    assert.equal(okRes.ok, true, okRes.reason);
    assert.equal(okRes.contract.filter((c) => c.kind === 'collection').length, 2);

    const nested = `<ul>{#each groups as g}<li>{#each g.items as item}<span>{item.n}</span>{/each}</li>{/each}</ul>`;
    const badRes = analyzeSvelteMarkup(nested, parse);
    assert.equal(badRes.ok, false);
    assert.match(badRes.reason, /nested/);
  });

  it('falls back for constructs a detached preview cannot support', () => {
    const cases = [
      [`<div><Card title={t} /></div>`, /component tag/],
      [`<input bind:value={query} />`, /bind:/],
      [`<div use:tooltip>{t}</div>`, /use:/],
      [`<div>{#await p}<p>wait</p>{:then v}<p>{v}</p>{/await}</div>`, /await/],
      [`<div><script>let x = 1;<\/script><p>{t}</p></div>`, /script/],
      [`<div {...rest}>{t}</div>`, /spread/],
    ];
    for (const [src, reason] of cases) {
      const res = analyzeSvelteMarkup(src, parse);
      assert.equal(res.ok, false, `expected fallback for: ${src}`);
      assert.match(res.reason, reason, src);
    }
  });

  it('treats class directives as condition props', () => {
    const src = `<div class:active={isActive}><span>{label}</span></div>`;
    const res = analyzeSvelteMarkup(src, parse);
    assert.equal(res.ok, true, res.reason);
    const cond = res.contract.find((c) => c.expr === 'isActive');
    assert.equal(cond.kind, 'condition');
  });

  it('round-trips every supported corpus snippet', () => {
    const corpus = [
      PIT_BOARD,
      `<ul>{#each data.stages as s, i (s.id)}<li>{s.name}</li>{/each}</ul>`,
      `<section>{#if user.loggedIn}<p>{user.name}</p>{:else}<p>guest</p>{/if}</section>`,
      `<div>{@html bodyHtml}</div>`,
      `<article>{#each posts as post}<h2>{post.title}</h2>{#if post.pinned}<em>pinned</em>{/if}{/each}</article>`,
      `<p title={hint}>{copy} and {copy}</p>`,
      `<div>{@const label = row.name}<span>{label}</span></div>`,
      `<nav>{#each links as link}<a href={link.href}>{link.text}</a>{/each}</nav>`,
    ];
    for (const src of corpus) {
      const res = analyzeSvelteMarkup(src, parse);
      assert.equal(res.ok, true, `${res.reason} in: ${src}`);
      const restored = restoreSvelteMarkup(res.markupWithProps, res.contract, parse);
      assert.equal(restored.ok, true, src);
      assert.equal(restored.markup, src, `round trip failed for: ${src}`);
    }
  });

  it('generates a props script that compiles with real svelte', () => {
    const res = analyzeSvelteMarkup(PIT_BOARD, parse);
    const component = `${buildPropsScriptV2(res.contract)}\n${res.markupWithProps}\n<style>\n  .stage { display: flex; }\n</style>\n`;
    const compiled = compile(component, { generate: 'client' });
    assert.ok(compiled.js.code.length > 0);
    const fatal = (compiled.warnings || []).filter((w) => /error/i.test(w.code || ''));
    assert.deepEqual(fatal, []);
  });

  it('collectRootIdentifiers skips member properties and object keys', () => {
    const ast = parse(`<p>{fmt(user.name, { width: cols })}</p>`, { modern: true });
    const tag = ast.fragment.nodes[0].fragment.nodes[0];
    const roots = collectRootIdentifiers(tag.expression);
    assert.deepEqual([...roots].sort(), ['cols', 'fmt', 'user']);
  });

  it('derivePropName picks stable tails', () => {
    assert.equal(derivePropName('stages'), 'stages');
    assert.equal(derivePropName('data.stages'), 'stages');
    assert.equal(derivePropName('rows[0].label'), 'label');
    assert.equal(derivePropName('a + b'), 'value');
  });
});

describe('keyed each blocks', () => {
  it('records a keyField for member keys and keeps the key in the scaffold', () => {
    const src = `<ul>{#each expenses as expense, i (expense.id)}<li class="row"><strong>{expense.name}</strong></li>{/each}</ul>`;
    const res = analyzeSvelteMarkup(src, parse);
    assert.equal(res.ok, true, res.reason);
    const collection = res.contract.find((c) => c.kind === 'collection');
    assert.equal(collection.item.keyField, 'id');
    assert.match(res.markupWithProps, /\(expense\.id\)/);
    const restored = restoreSvelteMarkup(res.markupWithProps, res.contract, parse);
    assert.equal(restored.markup, src);
  });

  it('needs no keyField when the key is the item or the index', () => {
    for (const src of [
      `<ul>{#each rows as r (r)}<li>{r.x}</li>{/each}</ul>`,
      `<ul>{#each rows as r, i (i)}<li>{r.x}</li>{/each}</ul>`,
    ]) {
      const res = analyzeSvelteMarkup(src, parse);
      assert.equal(res.ok, true, `${res.reason} in ${src}`);
      const collection = res.contract.find((c) => c.kind === 'collection');
      assert.equal(collection.item.keyField, undefined, src);
    }
  });

  it('falls back for keys a detached preview cannot hydrate distinctly', () => {
    const cases = [
      [`<ul>{#each rows as r (globalThing)}<li>{r.x}</li>{/each}</ul>`, /not derived from the loop item/],
      [`<ul>{#each rows as r (makeKey(r))}<li>{r.x}</li>{/each}</ul>`, /complex each key/],
      [`<ul>{#each rows as r (r.name)}<li>{r.name}</li>{/each}</ul>`, /also a displayed field/],
    ];
    for (const [src, reason] of cases) {
      const res = analyzeSvelteMarkup(src, parse);
      assert.equal(res.ok, false, `expected fallback for ${src}`);
      assert.match(res.reason, reason, src);
    }
  });
});

describe('review regressions: reserved prop names', () => {
  it('never derives a JS reserved word as a prop name (M5)', () => {
    for (const [src, expected] of [
      [`<div>{item.class}</div>`, 'classValue'],
      [`<div>{cfg.default}</div>`, 'defaultValue'],
      [`<div>{a.for}</div>`, 'forValue'],
    ]) {
      const res = analyzeSvelteMarkup(src, parse);
      assert.equal(res.ok, true, res.reason);
      assert.equal(res.contract[0].prop, expected, src);
      // The generated stub must actually compile.
      const stub = `${buildPropsScriptV2(res.contract)}\n${res.markupWithProps}\n`;
      const compiled = compile(stub, { generate: 'client' });
      assert.ok(compiled.js.code.length > 0, src);
      // And restore back to the original expression.
      const restored = restoreSvelteMarkup(res.markupWithProps, res.contract, parse);
      assert.equal(restored.markup, src);
    }
  });
});

describe('review regressions: directives', () => {
  it('class directives carry a className probe for live hydration', () => {
    const src = `<div class:active={isActive}><span>{label}</span></div>`;
    const res = analyzeSvelteMarkup(src, parse);
    assert.equal(res.ok, true, res.reason);
    const cond = res.contract.find((c) => c.expr === 'isActive');
    assert.deepEqual(cond.probe, { className: 'active' });
  });

  it('style directives with dynamic values fall back to source-preview', () => {
    const res = analyzeSvelteMarkup(`<div style:opacity={fade}>x</div>`, parse);
    assert.equal(res.ok, false);
    assert.match(res.reason, /style:opacity/);
  });

  it('style directives with static values stay supported', () => {
    const res = analyzeSvelteMarkup(`<div style:color="red">{note}</div>`, parse);
    assert.equal(res.ok, true, res.reason);
  });
});

describe('review regressions: mixed and global identifiers', () => {
  it('falls back for expressions mixing loop bindings with outer names', () => {
    const src = `<ul>{#each rows as r}<li>{fmt(r.label)}</li>{/each}</ul>`;
    const res = analyzeSvelteMarkup(src, parse);
    assert.equal(res.ok, false);
    assert.match(res.reason, /mixing loop and outer identifiers/);
  });

  it('treats known globals as neither free nor bound', () => {
    // Global + bound: stays verbatim, no prop, no fallback.
    const okRes = analyzeSvelteMarkup(`<ul>{#each rows as r}<li>{Math.round(r.score)}</li>{/each}</ul>`, parse);
    assert.equal(okRes.ok, true, okRes.reason);
    assert.equal(okRes.contract.some((c) => c.prop === 'round'), false);
    assert.match(okRes.markupWithProps, /\{Math\.round\(r\.score\)\}/);

    // Pure-global expression at top level: no prop minted either.
    const topRes = analyzeSvelteMarkup(`<p>{JSON.stringify(navigator.language)}</p>`, parse);
    assert.equal(topRes.ok, true, topRes.reason);
    assert.equal(topRes.contract.length, 0);
  });
});

describe('review regressions: attribute slots and hydration honesty', () => {
  it('records attribute-bound values as attr slots', () => {
    const src = `<nav>{#each links as link}<a class="nav-link" href={link.href}>{link.text}</a>{/each}</nav>`;
    const res = analyzeSvelteMarkup(src, parse);
    assert.equal(res.ok, true, res.reason);
    const item = res.contract.find((c) => c.kind === 'collection').item;
    assert.deepEqual(item.textSlots.map((s) => s.key), ['text']);
    assert.deepEqual(item.attrSlots, [{ key: 'href', expr: 'link.href', attr: 'href', tag: 'a', classes: ['nav-link'] }]);
  });

  it('falls back for per-item expressions the shallow item cannot represent', () => {
    for (const src of [
      `<ul>{#each rows as r}<li>{r.meta.label}</li>{/each}</ul>`,
      `<ul>{#each rows as r}<li>{r.format()}</li>{/each}</ul>`,
      `<ul>{#each rows as r}<li>{r}</li>{/each}</ul>`,
    ]) {
      const res = analyzeSvelteMarkup(src, parse);
      assert.equal(res.ok, false, `expected fallback for ${src}`);
      assert.match(res.reason, /cannot hydrate/);
    }
  });

  it('index-only expressions need no slot', () => {
    const res = analyzeSvelteMarkup(`<ul>{#each rows as r, i}<li>{i}: {r.name}</li>{/each}</ul>`, parse);
    assert.equal(res.ok, true, res.reason);
    const item = res.contract.find((c) => c.kind === 'collection').item;
    assert.deepEqual(item.textSlots.map((s) => s.key), ['name']);
  });

  it('style directives mixing loop and outer names fall back', () => {
    const res = analyzeSvelteMarkup(`<ul>{#each rows as r}<li style:width={base + r.pct}>x</li>{/each}</ul>`, parse);
    assert.equal(res.ok, false);
    assert.match(res.reason, /mixing loop and outer identifiers/);
  });
});

describe('review regressions: each-key restore scoping', () => {
  it('leaves a key that reads the loop binding alone when a prop shares its name', () => {
    // The corruption shape: prop `name` maps back to `user.name`, and the
    // loop context is ALSO called `name`. The key evaluates per item, so its
    // `name` is the loop binding, never the prop; restoring it used to write
    // `(user.name.id)` into the route.
    const contract = [{ prop: 'name', expr: 'user.name', kind: 'text' }];
    const markup = `<p>{name}</p>
<ul>
  {#each people as name (name.id)}
    <li>{name.first}</li>
  {/each}
</ul>`;
    const restored = restoreSvelteMarkup(markup, contract, parse);
    assert.equal(restored.ok, true, restored.reason);
    assert.match(restored.markup, /<p>\{user\.name\}<\/p>/, 'free usage restores to the expression');
    assert.match(restored.markup, /\(name\.id\)/, 'the key keeps the loop binding');
    assert.doesNotMatch(restored.markup, /\(user\.name\.id\)/);
    assert.match(restored.markup, /\{name\.first\}/, 'the body keeps the loop binding');
  });
});
