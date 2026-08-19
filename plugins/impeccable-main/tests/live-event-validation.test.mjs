/**
 * Unit tests for live-event-validation.mjs
 * Run with: node --test tests/live-event-validation.test.mjs
 */

import { describe, it } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';

import { AGENT_PHASES, CLIENT_EVENT_TYPES, validateEvent } from '../skill/scripts/live/event-validation.mjs';
import { VISUAL_ACTIONS } from '../skill/scripts/live/vocabulary.mjs';

const VALID_ID = 'a1b2c3d4';

describe('validateEvent — insert generate', () => {
  const baseInsert = {
    type: 'generate',
    id: VALID_ID,
    mode: 'insert',
    count: 3,
    pageUrl: '/',
    insert: {
      position: 'after',
      anchor: { tagName: 'section', classes: ['hero'] },
    },
    placeholder: { width: 320, height: 80 },
    freeformPrompt: 'Add a testimonial strip',
  };

  it('accepts a valid insert generate event', () => {
    assert.equal(validateEvent(baseInsert), null);
  });

  it('accepts insert with annotations only (no prompt)', () => {
    assert.equal(validateEvent({
      ...baseInsert,
      freeformPrompt: undefined,
      comments: [{ x: 1, y: 2, text: 'headline' }],
    }), null);
  });

  it('rejects insert without prompt or annotations', () => {
    const err = validateEvent({ ...baseInsert, freeformPrompt: '  ' });
    assert.match(err, /freeformPrompt or annotations/i);
  });

  it('rejects insert without placeholder dimensions', () => {
    assert.match(validateEvent({ ...baseInsert, placeholder: null }), /placeholder/i);
    assert.match(validateEvent({ ...baseInsert, placeholder: { width: 100 } }), /placeholder/i);
  });

  it('rejects invalid insert position', () => {
    assert.match(
      validateEvent({ ...baseInsert, insert: { ...baseInsert.insert, position: 'inside' } }),
      /before or after/i,
    );
  });

  it('rejects insert without anchor context', () => {
    assert.match(
      validateEvent({ ...baseInsert, insert: { position: 'after', anchor: {} } }),
      /insert\.anchor/i,
    );
  });

  it('does not require action for insert mode', () => {
    assert.equal(validateEvent({ ...baseInsert, action: undefined }), null);
  });
});

describe('validateEvent — replace generate (regression)', () => {
  it('still requires action and element for replace mode', () => {
    assert.match(
      validateEvent({
        type: 'generate',
        id: VALID_ID,
        count: 2,
        action: 'polish',
      }),
      /element context/i,
    );
    assert.match(
      validateEvent({
        type: 'generate',
        id: VALID_ID,
        count: 2,
        element: { outerHTML: '<div/>' },
      }),
      /invalid action/i,
    );
    assert.equal(
      validateEvent({
        type: 'generate',
        id: VALID_ID,
        count: 2,
        action: 'polish',
        element: { outerHTML: '<div/>' },
      }),
      null,
    );
  });
});

describe('validateEvent — mount acknowledgements', () => {
  it('accepts a well-formed variant_mounted ack with and without a url', () => {
    assert.equal(validateEvent({ type: 'variant_mounted', id: VALID_ID, variant: 2 }), null);
    assert.equal(validateEvent({
      type: 'variant_mounted',
      id: VALID_ID,
      variant: 1,
      url: 'http://localhost:5173/.impeccable/live/preview/v1.svelte',
    }), null);
  });

  it('rejects malformed variant_mounted acks', () => {
    assert.match(validateEvent({ type: 'variant_mounted', id: 'nope', variant: 1 }), /malformed id/);
    assert.match(validateEvent({ type: 'variant_mounted', id: VALID_ID, variant: 0 }), /variant/);
    assert.match(validateEvent({ type: 'variant_mounted', id: VALID_ID, variant: 1.5 }), /variant/);
    assert.match(validateEvent({ type: 'variant_mounted', id: VALID_ID }), /variant/);
    assert.match(validateEvent({ type: 'variant_mounted', id: VALID_ID, variant: 1, url: 42 }), /url must be string/);
    assert.match(
      validateEvent({ type: 'variant_mounted', id: VALID_ID, variant: 1, url: 'u'.repeat(2001) }),
      /url too long/,
    );
  });

  it('accepts a well-formed variant_mount_failed report', () => {
    assert.equal(validateEvent({
      type: 'variant_mount_failed',
      id: VALID_ID,
      variant: 3,
      url: '/preview/v3.svelte',
      error: 'Failed to fetch dynamically imported module',
    }), null);
  });

  it('requires url and error on variant_mount_failed and caps their length', () => {
    const base = { type: 'variant_mount_failed', id: VALID_ID, variant: 1, url: '/v1.svelte', error: 'boom' };
    assert.match(validateEvent({ ...base, url: undefined }), /url required/);
    assert.match(validateEvent({ ...base, url: '   ' }), /url required/);
    assert.match(validateEvent({ ...base, error: undefined }), /error required/);
    assert.match(validateEvent({ ...base, error: '  ' }), /error required/);
    assert.match(validateEvent({ ...base, url: 'u'.repeat(2001) }), /url too long/);
    assert.match(validateEvent({ ...base, error: 'e'.repeat(1001) }), /error too long/);
    assert.match(validateEvent({ ...base, id: 'ZZZZ' }), /malformed id/);
    assert.match(validateEvent({ ...base, variant: '2' }), /variant/);
  });
});

describe('validateEvent — worker progress', () => {
  it('accepts every phase the server emits and rejects malformed telemetry', () => {
    for (const phase of AGENT_PHASES) {
      assert.equal(
        validateEvent({ type: 'agent_phase', id: VALID_ID, phase, durationMs: 123 }),
        null,
        'event=live_event_validation.agent_phase actor=server operation=validate risk=server_phase_rejected phase=' + phase,
      );
    }
    assert.match(validateEvent({ type: 'agent_phase', id: VALID_ID, phase: 'Not valid' }), /phase/);
    assert.match(validateEvent({ type: 'agent_phase', id: VALID_ID, phase: 'all_variants_ready', durationMs: -1 }), /durationMs/);
  });

  it('rejects a phase no component models instead of ranking it as unknown', () => {
    // These were carried in the browser's PHASE_RANK table and its status
    // strings long after the server stopped emitting them. A phase nothing
    // sends is a phase nothing can render.
    for (const retired of [
      'first_variant_generating',
      'first_variant_validating',
      'remaining_variants_generating',
      'remaining_variants_validating',
      'variant_parameters_generating',
      'variant_parameters_validating',
      'parameters_ready',
    ]) {
      assert.match(
        validateEvent({ type: 'agent_phase', id: VALID_ID, phase: retired }),
        /unknown phase/,
        'event=live_event_validation.retired_phase actor=server operation=validate risk=dead_enum_value_revived phase=' + retired,
      );
    }
    assert.match(validateEvent({ type: 'agent_phase', id: VALID_ID, phase: '' }), /missing phase/);
  });
});

describe('protocol vocabulary', () => {
  const SOURCE = readFileSync(
    fileURLToPath(new URL('../skill/scripts/live/event-validation.mjs', import.meta.url)),
    'utf-8',
  );

  it('validates exactly the event types the vocabulary advertises', () => {
    for (const type of CLIENT_EVENT_TYPES) {
      assert.equal(
        /^Unknown event type/.test(String(validateEvent({ type }))),
        false,
        'event=live_vocabulary.client_event_types actor=browser operation=validate risk=advertised_type_unroutable type=' + type,
      );
    }
    assert.match(validateEvent({ type: 'not_a_real_event' }), /^Unknown event type/);
  });

  it('keeps the enums in the vocabulary module rather than inlined here', () => {
    assert.doesNotMatch(
      SOURCE,
      /\[\^a-z\]\{1,63\}|\{1,63\}/,
      'agent_phase must be checked against the enum, not a shape pattern',
    );
    assert.match(SOURCE, /from '\.\/vocabulary\.mjs'/);
  });

  it('accepts every palette action as a generate action', () => {
    for (const action of VISUAL_ACTIONS) {
      assert.equal(validateEvent({
        type: 'generate',
        id: VALID_ID,
        count: 1,
        action,
        element: { outerHTML: '<button>Go</button>' },
      }), null);
    }
  });
});
