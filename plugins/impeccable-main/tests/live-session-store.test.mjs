/**
 * Tests for durable live-session state.
 * Run with: node --test tests/live-session-store.test.mjs
 */

import { describe, it, beforeEach, afterEach } from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import { mkdirSync, mkdtempSync, rmSync, appendFileSync, readFileSync, statSync, writeFileSync } from 'node:fs';
import { join } from 'node:path';
import { tmpdir } from 'node:os';

import { createLiveSessionStore } from '../skill/scripts/live/session-store.mjs';
import {
  getLegacyLiveSessionsDir,
  getLiveAnnotationsDir,
  getLiveSessionsDir,
} from '../skill/scripts/lib/impeccable-paths.mjs';

describe('live-session-store', () => {
  let tmp;

  beforeEach(() => {
    tmp = mkdtempSync(join(tmpdir(), 'impeccable-session-store-'));
  });

  afterEach(() => {
    rmSync(tmp, { recursive: true, force: true });
  });

  it('rebuilds an active snapshot from an append-only journal after process restart', () => {
    const store = createLiveSessionStore({ cwd: tmp, sessionId: 'session-a' });
    store.appendEvent({
      type: 'generate',
      id: 'session-a',
      action: 'polish',
      count: 3,
      pageUrl: 'http://localhost:4321/',
      element: { outerHTML: '<section class="hero">Hero</section>', tagName: 'section' },
      screenshotPath: join(getLiveAnnotationsDir(tmp), 'session-a.png'),
    });
    store.appendEvent({ type: 'variants_ready', id: 'session-a', file: 'src/pages/index.astro', arrivedVariants: 3 });
    store.appendEvent({ type: 'accept_intent', id: 'session-a', variantId: 2, paramValues: { density: 'packed' } });

    const restarted = createLiveSessionStore({ cwd: tmp, sessionId: 'session-a' });
    const snapshot = restarted.getSnapshot('session-a');

    assert.equal(snapshot.id, 'session-a');
    assert.equal(snapshot.phase, 'accept_requested');
    assert.equal(snapshot.expectedVariants, 3);
    assert.equal(snapshot.arrivedVariants, 3);
    assert.equal(snapshot.sourceFile, 'src/pages/index.astro');
    assert.equal(snapshot.visibleVariant, 2);
    assert.deepEqual(snapshot.paramValues, { density: 'packed' });
    assert.equal(snapshot.annotationArtifacts[0].path.endsWith('session-a.png'), true);

    const active = restarted.listActiveSessions();
    assert.equal(
      active.length,
      1,
      'event=live_session_store.active_restart actor=agent operation=list_active_sessions risk=server_restart_loses_live_state expected=one active session actual=' + active.length + ' suggestion=inspect journal replay and completed phase filtering',
    );
    assert.equal(active[0].id, 'session-a');
  });

  it('persists the progressive variant plan across worker restarts', () => {
    const store = createLiveSessionStore({ cwd: tmp, sessionId: 'planned-session' });
    const plan = {
      identityLock: ['Preserve copy'],
      directions: [
        { variantId: 1, name: 'Hierarchy', axis: 'scale', intent: 'Increase hierarchy' },
        { variantId: 2, name: 'Composition', axis: 'layout', intent: 'Recompose the root' },
        { variantId: 3, name: 'Rhythm', axis: 'spacing', intent: 'Increase rhythm' },
      ],
    };
    store.appendEvent({ type: 'generate', id: 'planned-session', count: 3 });
    store.appendEvent({ type: 'variant_plan', id: 'planned-session', plan });
    store.appendEvent({ type: 'checkpoint', id: 'planned-session', revision: 1, arrivedVariants: 1 });

    const restarted = createLiveSessionStore({ cwd: tmp, sessionId: 'planned-session' });
    assert.deepEqual(restarted.getSnapshot('planned-session').variantPlan, plan);
  });

  it('tombstones generation on early accept and ignores late generation writes', () => {
    const store = createLiveSessionStore({ cwd: tmp, sessionId: 'early-accept' });
    store.appendEvent({
      type: 'generate',
      id: 'early-accept',
      action: 'polish',
      count: 3,
      element: { outerHTML: '<section>Hero</section>', tagName: 'section' },
    });
    store.appendEvent({
      type: 'checkpoint',
      id: 'early-accept',
      revision: 1,
      phase: 'cycling',
      arrivedVariants: 1,
      visibleVariant: 1,
    });
    store.appendEvent({ type: 'accept', id: 'early-accept', variantId: '1' });
    store.appendEvent({
      type: 'checkpoint',
      id: 'early-accept',
      revision: 2,
      phase: 'variants_ready',
      arrivedVariants: 3,
      visibleVariant: 3,
    });
    store.appendEvent({
      type: 'agent_done',
      id: 'early-accept',
      file: 'src/App.jsx',
      arrivedVariants: 3,
    });

    const snapshot = store.getSnapshot('early-accept');
    assert.equal(snapshot.phase, 'accept_requested');
    assert.equal(snapshot.generationCanceled, true);
    assert.equal(snapshot.cancelReason, 'accept');
    assert.equal(snapshot.arrivedVariants, 1);
    assert.equal(snapshot.visibleVariant, 1);
    assert.equal(
      snapshot.diagnostics.some((entry) => entry.error === 'late_generation_event_ignored'),
      true,
    );
  });

  it('reports corrupted journal lines while preserving valid prior events', () => {
    const store = createLiveSessionStore({ cwd: tmp, sessionId: 'corrupt-session' });
    store.appendEvent({
      type: 'generate',
      id: 'corrupt-session',
      action: 'layout',
      count: 2,
      element: { outerHTML: '<div>Card</div>', tagName: 'div' },
    });

    appendFileSync(join(getLiveSessionsDir(tmp), 'corrupt-session.jsonl'), '{not json}\n');

    const restarted = createLiveSessionStore({ cwd: tmp, sessionId: 'corrupt-session' });
    const snapshot = restarted.getSnapshot('corrupt-session');

    assert.equal(snapshot.phase, 'generate_requested');
    assert.equal(snapshot.expectedVariants, 2);
    assert.equal(snapshot.diagnostics.length, 1);
    assert.match(snapshot.diagnostics[0].error, /journal_parse_failed/);
  });

  it('does not duplicate parse diagnostics when valid entries follow a corrupted journal line', () => {
    const dir = getLiveSessionsDir(tmp);
    mkdirSync(dir, { recursive: true });
    appendFileSync(join(dir, 'corrupt-then-valid.jsonl'), '{not json}\n');
    appendFileSync(join(dir, 'corrupt-then-valid.jsonl'), JSON.stringify({
      seq: 1,
      id: 'corrupt-then-valid',
      type: 'generate',
      ts: new Date().toISOString(),
      event: {
        type: 'generate',
        id: 'corrupt-then-valid',
        action: 'polish',
        count: 2,
        element: { outerHTML: '<h1>Title</h1>', tagName: 'h1' },
      },
    }) + '\n');

    const store = createLiveSessionStore({ cwd: tmp, sessionId: 'corrupt-then-valid' });
    const snapshot = store.getSnapshot('corrupt-then-valid');
    const parseDiagnostics = snapshot.diagnostics.filter((d) => d.error === 'journal_parse_failed');

    assert.equal(snapshot.phase, 'generate_requested');
    assert.equal(
      parseDiagnostics.length,
      1,
      'event=live_session_store.duplicate_parse_diagnostic actor=store operation=journal_replay risk=duplicate_status_noise expected=1 actual=' + parseDiagnostics.length,
    );
  });

  it('preserves zero-valued checkpoint revisions and empty explicit fields', () => {
    const store = createLiveSessionStore({ cwd: tmp, sessionId: 'zero-checkpoint' });
    store.appendEvent({
      type: 'checkpoint',
      id: 'zero-checkpoint',
      revision: 0,
      phase: '',
      owner: '',
      arrivedVariants: 0,
      visibleVariant: 0,
      paramValues: { density: 0 },
    });

    const snapshot = store.getSnapshot('zero-checkpoint');
    assert.equal(
      snapshot.checkpointRevision,
      0,
      'event=live_session_store.zero_checkpoint_revision actor=browser operation=checkpoint_replay risk=zero_revision_dropped expected=0 actual=' + snapshot.checkpointRevision,
    );
    assert.equal(snapshot.phase, '');
    assert.equal(snapshot.activeOwner, '');
    assert.equal(snapshot.visibleVariant, 0);
    assert.deepEqual(snapshot.paramValues, { density: 0 });
  });

  it('ignores stale checkpoints and keeps the newest browser state', () => {
    const store = createLiveSessionStore({ cwd: tmp, sessionId: 'checkpoint-session' });
    store.appendEvent({
      type: 'generate',
      id: 'checkpoint-session',
      action: 'layout',
      count: 3,
      element: { outerHTML: '<section>Hero</section>', tagName: 'section' },
    });
    store.appendEvent({ type: 'checkpoint', id: 'checkpoint-session', revision: 5, phase: 'cycling', visibleVariant: 3, paramValues: { density: 'packed' } });
    store.appendEvent({ type: 'checkpoint', id: 'checkpoint-session', revision: 2, phase: 'cycling', visibleVariant: 1, paramValues: { density: 'airy' } });

    const snapshot = store.getSnapshot('checkpoint-session');
    assert.equal(snapshot.checkpointRevision, 5);
    assert.equal(snapshot.visibleVariant, 3);
    assert.deepEqual(snapshot.paramValues, { density: 'packed' });
    assert.equal(
      snapshot.diagnostics.some((d) => d.error === 'stale_checkpoint_ignored' && d.revision === 2),
      true,
      'event=live_session_store.stale_checkpoint actor=browser operation=checkpoint_replay risk=old_browser_state_overwrites_newer_choice expected=stale diagnostic actual=' + JSON.stringify(snapshot.diagnostics),
    );
  });

  it('tracks publication and browser checkpoint revisions independently', () => {
    const store = createLiveSessionStore({ cwd: tmp, sessionId: 'split-revisions' });
    store.appendEvent({
      type: 'generate', id: 'split-revisions', count: 3,
      element: { outerHTML: '<section>Hero</section>', tagName: 'section' },
    });
    store.appendEvent({
      type: 'checkpoint', id: 'split-revisions', revision: 8, revisionDomain: 'browser',
      owner: 'browser-a', phase: 'cycling', visibleVariant: 2,
    });
    store.appendEvent({
      type: 'checkpoint', id: 'split-revisions', revision: 3, revisionDomain: 'publication',
      reason: 'variants_progress', phase: 'cycling', arrivedVariants: 3,
    });

    const snapshot = store.getSnapshot('split-revisions');
    assert.equal(snapshot.browserCheckpointRevision, 8);
    assert.equal(snapshot.checkpointRevision, 8);
    assert.equal(snapshot.publicationCheckpointRevision, 3);
    assert.equal(snapshot.visibleVariant, 2);
    assert.equal(snapshot.arrivedVariants, 3);
    assert.equal(snapshot.diagnostics.some((entry) => entry.error === 'stale_checkpoint_ignored'), false);
  });

  it('keeps carbonize-required accepted sessions active until explicit completion', () => {
    const store = createLiveSessionStore({ cwd: tmp, sessionId: 'carbonize-session' });
    store.appendEvent({
      type: 'accept',
      id: 'carbonize-session',
      variantId: '2',
      paramValues: { tone: 'sharp' },
    });
    store.appendEvent({ type: 'agent_done', id: 'carbonize-session', file: 'src/App.jsx', carbonize: true });

    const snapshot = store.getSnapshot('carbonize-session');
    assert.equal(
      snapshot.phase,
      'carbonize_required',
      'event=live_session_store.carbonize_required actor=agent operation=accept_ack risk=carbonize_session_hidden_from_recovery expected=carbonize_required actual=' + snapshot.phase,
    );
    assert.equal(snapshot.sourceFile, 'src/App.jsx');
    assert.equal(snapshot.pendingEvent, null);
    assert.equal(store.listActiveSessions().some((s) => s.id === 'carbonize-session'), true);

    store.appendEvent({ type: 'complete', id: 'carbonize-session' });
    const completed = store.getSnapshot('carbonize-session', { includeCompleted: true });
    assert.equal(completed.phase, 'completed');
    assert.equal(store.listActiveSessions().some((s) => s.id === 'carbonize-session'), false);
  });

  it('clears pending events when an agent error is acknowledged', () => {
    const store = createLiveSessionStore({ cwd: tmp, sessionId: 'error-session' });
    store.appendEvent({
      type: 'generate',
      id: 'error-session',
      action: 'polish',
      count: 1,
      element: { outerHTML: '<button>Try</button>', tagName: 'button' },
    });
    store.appendEvent({ type: 'agent_error', id: 'error-session', message: 'accept failed' });

    const snapshot = store.getSnapshot('error-session');
    assert.equal(snapshot.phase, 'agent_error');
    assert.equal(snapshot.pendingEvent, null);
    assert.equal(snapshot.pendingEventSeq, null);
    assert.equal(
      store.listActiveSessions()[0].pendingEvent,
      null,
      'event=live_session_store.agent_error_ack actor=agent operation=restart_replay risk=acknowledged_error_event_redelivered expected=null actual=' + JSON.stringify(store.listActiveSessions()[0].pendingEvent),
    );
  });

  it('keeps completed sessions auditable but excludes them from active sessions by default', () => {
    const store = createLiveSessionStore({ cwd: tmp, sessionId: 'done-session' });
    store.appendEvent({
      type: 'generate',
      id: 'done-session',
      action: 'bolder',
      count: 1,
      element: { outerHTML: '<h1>Title</h1>', tagName: 'h1' },
    });
    store.appendEvent({ type: 'agent_done', id: 'done-session', file: 'src/pages/index.astro' });
    store.appendEvent({ type: 'complete', id: 'done-session' });

    const active = store.listActiveSessions();
    const completed = store.getSnapshot('done-session', { includeCompleted: true });

    assert.equal(active.length, 0);
    assert.equal(completed.phase, 'completed');
    assert.equal(completed.sourceFile, 'src/pages/index.astro');
  });

  it('writes a rebuildable snapshot cache without making it authoritative', () => {
    const store = createLiveSessionStore({ cwd: tmp, sessionId: 'cache-session' });
    store.appendEvent({
      type: 'generate',
      id: 'cache-session',
      action: 'colorize',
      count: 2,
      element: { outerHTML: '<div>Palette</div>', tagName: 'div' },
    });

    const snapshotPath = join(getLiveSessionsDir(tmp), 'cache-session.snapshot.json');
    const cached = JSON.parse(readFileSync(snapshotPath, 'utf-8'));
    assert.equal(cached.phase, 'generate_requested');

    // Simulate stale snapshot cache. Restart must prefer journal truth and repair cache.
    appendFileSync(snapshotPath, '');
    const restarted = createLiveSessionStore({ cwd: tmp, sessionId: 'cache-session' });
    restarted.appendEvent({ type: 'agent_done', id: 'cache-session', file: 'src/pages/index.astro' });
    const repaired = JSON.parse(readFileSync(snapshotPath, 'utf-8'));

    assert.equal(repaired.phase, 'variants_ready');
    assert.equal(repaired.sourceFile, 'src/pages/index.astro');
  });

  it('recovers legacy journals from .impeccable-live/sessions', () => {
    const legacyDir = getLegacyLiveSessionsDir(tmp);
    mkdirSync(legacyDir, { recursive: true });
    appendFileSync(join(legacyDir, 'legacy-session.jsonl'), JSON.stringify({
      seq: 1,
      id: 'legacy-session',
      type: 'generate',
      ts: new Date().toISOString(),
      event: {
        type: 'generate',
        id: 'legacy-session',
        action: 'polish',
        count: 2,
        element: { outerHTML: '<section>Legacy</section>', tagName: 'section' },
      },
    }) + '\n');

    const store = createLiveSessionStore({ cwd: tmp, sessionId: 'legacy-session' });
    const snapshot = store.getSnapshot('legacy-session');

    assert.equal(snapshot.phase, 'generate_requested');
    assert.equal(snapshot.expectedVariants, 2);
    assert.equal(store.listActiveSessions().some((s) => s.id === 'legacy-session'), true);

    store.appendEvent({ type: 'agent_done', id: 'legacy-session', file: 'src/App.jsx' });
    const restarted = createLiveSessionStore({ cwd: tmp, sessionId: 'legacy-session' });
    const migratedSnapshot = restarted.getSnapshot('legacy-session');
    assert.equal(migratedSnapshot.phase, 'variants_ready');
    assert.equal(migratedSnapshot.expectedVariants, 2);
    assert.equal(migratedSnapshot.sourceFile, 'src/App.jsx');
  });

  it('records generation phase timings without replacing the workflow phase', () => {
    const store = createLiveSessionStore({ cwd: tmp, sessionId: 'phase-session' });
    store.appendEvent({
      type: 'generate',
      id: 'phase-session',
      count: 3,
      element: { classes: ['hero'] },
    });
    store.appendEvent({
      type: 'agent_phase',
      id: 'phase-session',
      phase: 'source_ready',
      at: 1234,
      durationMs: 42,
    });

    const snapshot = store.getSnapshot('phase-session');
    assert.equal(snapshot.phase, 'generate_requested');
    assert.equal(snapshot.generationPhase, 'source_ready');
    assert.deepEqual(snapshot.generationTimings.source_ready, { at: 1234, durationMs: 42 });
  });

  describe('derived-state cache', () => {
    /**
     * Counts reads of one journal while `body` runs. The store patches nothing
     * to make this observable: it calls fs.readFileSync on the module object
     * this test also holds, so a replay is directly countable.
     */
    function countJournalReads(journalPath, body) {
      const original = fs.readFileSync;
      let reads = 0;
      fs.readFileSync = (target, ...rest) => {
        if (String(target) === journalPath) reads++;
        return original(target, ...rest);
      };
      try {
        body();
      } finally {
        fs.readFileSync = original;
      }
      return reads;
    }

    function countWrites(body) {
      const originalWrite = fs.writeFileSync;
      const originalAppend = fs.appendFileSync;
      let writes = 0;
      fs.writeFileSync = (...args) => { writes++; return originalWrite(...args); };
      fs.appendFileSync = (...args) => { writes++; return originalAppend(...args); };
      try {
        body();
      } finally {
        fs.writeFileSync = originalWrite;
        fs.appendFileSync = originalAppend;
      }
      return writes;
    }

    it('appends without replaying the journal it just wrote', () => {
      const store = createLiveSessionStore({ cwd: tmp, sessionId: 'append-cost' });
      store.appendEvent({ type: 'generate', id: 'append-cost', count: 3, element: { classes: ['hero'] } });
      const journalPath = join(getLiveSessionsDir(tmp), 'append-cost.jsonl');

      const reads = countJournalReads(journalPath, () => {
        for (let revision = 1; revision <= 25; revision++) {
          store.appendEvent({ type: 'checkpoint', id: 'append-cost', revision, phase: 'cycling', visibleVariant: 1 });
        }
      });

      assert.equal(
        reads,
        0,
        'event=live_session_store.append_replay actor=server operation=append_event risk=quadratic_journal_replay expected=0 journal reads actual=' + reads,
      );
      const snapshot = store.getSnapshot('append-cost');
      assert.equal(snapshot.checkpointRevision, 25);
      assert.equal(snapshot.expectedVariants, 3);
    });

    it('keeps a full replay equivalent to the incremental result', () => {
      const store = createLiveSessionStore({ cwd: tmp, sessionId: 'equivalence' });
      store.appendEvent({ type: 'generate', id: 'equivalence', count: 3, element: { classes: ['hero'] } });
      store.appendEvent({ type: 'checkpoint', id: 'equivalence', revision: 4, phase: 'cycling', visibleVariant: 2 });
      store.appendEvent({ type: 'checkpoint', id: 'equivalence', revision: 1, phase: 'cycling', visibleVariant: 9 });
      store.appendEvent({ type: 'variant_mounted', id: 'equivalence', variant: 2 });
      store.appendEvent({ type: 'variants_ready', id: 'equivalence', file: 'src/App.jsx', arrivedVariants: 3 });
      const incremental = store.getSnapshot('equivalence');

      // A store that has never seen this session has nothing cached and no
      // usable snapshot file for it either, so it takes the replay path.
      rmSync(join(getLiveSessionsDir(tmp), 'equivalence.snapshot.json'));
      const replayed = createLiveSessionStore({ cwd: tmp }).getSnapshot('equivalence');

      assert.deepEqual(
        { ...replayed, updatedAt: null },
        { ...incremental, updatedAt: null },
        'event=live_session_store.incremental_drift actor=store operation=apply_event risk=cached_snapshot_diverges_from_journal',
      );
    });

    it('answers reads without writing anything', () => {
      const store = createLiveSessionStore({ cwd: tmp, sessionId: 'read-only' });
      store.appendEvent({ type: 'generate', id: 'read-only', count: 2, element: { classes: ['hero'] } });
      const snapshotPath = join(getLiveSessionsDir(tmp), 'read-only.snapshot.json');
      const before = { stat: statSync(snapshotPath).mtimeMs, body: readFileSync(snapshotPath, 'utf-8') };

      // A separate instance stands in for live-status / live-resume, which run
      // in their own process against a session the server owns.
      const reader = createLiveSessionStore({ cwd: tmp });
      const writes = countWrites(() => {
        reader.getSnapshot('read-only');
        reader.listActiveSessions();
        reader.getSnapshot('read-only', { includeCompleted: true });
      });

      assert.equal(
        writes,
        0,
        'event=live_session_store.read_writes actor=agent operation=get_snapshot risk=status_command_mutates_session_state expected=0 writes actual=' + writes,
      );
      assert.equal(statSync(snapshotPath).mtimeMs, before.stat);
      assert.equal(readFileSync(snapshotPath, 'utf-8'), before.body);
    });

    it('reuses a snapshot file that still describes the journal, and skips one that does not', () => {
      const store = createLiveSessionStore({ cwd: tmp, sessionId: 'hydrate' });
      store.appendEvent({ type: 'generate', id: 'hydrate', count: 3, element: { classes: ['hero'] } });
      store.appendEvent({ type: 'variants_ready', id: 'hydrate', file: 'src/App.jsx', arrivedVariants: 3 });
      const journalPath = join(getLiveSessionsDir(tmp), 'hydrate.jsonl');
      const snapshotPath = join(getLiveSessionsDir(tmp), 'hydrate.snapshot.json');

      const fresh = createLiveSessionStore({ cwd: tmp });
      const hydratedReads = countJournalReads(journalPath, () => {
        assert.equal(fresh.getSnapshot('hydrate').arrivedVariants, 3);
      });
      assert.equal(
        hydratedReads,
        0,
        'event=live_session_store.list_replay actor=agent operation=list_active_sessions risk=every_status_call_replays_every_journal expected=0 journal reads actual=' + hydratedReads,
      );

      // A snapshot file whose recorded journal size no longer matches is not
      // evidence of anything; the journal wins.
      const stale = JSON.parse(readFileSync(snapshotPath, 'utf-8'));
      stale.arrivedVariants = 99;
      stale.__journalBytes = 1;
      writeFileSync(snapshotPath, JSON.stringify(stale, null, 2));
      const afterStale = createLiveSessionStore({ cwd: tmp }).getSnapshot('hydrate');
      assert.equal(
        afterStale.arrivedVariants,
        3,
        'event=live_session_store.stale_snapshot_trusted actor=store operation=get_snapshot risk=cache_outranks_journal expected=3 actual=' + afterStale.arrivedVariants,
      );
    });

    it('ignores a corrupt snapshot file instead of failing the read', () => {
      const store = createLiveSessionStore({ cwd: tmp, sessionId: 'corrupt-cache' });
      store.appendEvent({ type: 'generate', id: 'corrupt-cache', count: 2, element: { classes: ['hero'] } });
      writeFileSync(join(getLiveSessionsDir(tmp), 'corrupt-cache.snapshot.json'), '{ not json');

      const snapshot = createLiveSessionStore({ cwd: tmp }).getSnapshot('corrupt-cache');
      assert.equal(snapshot.phase, 'generate_requested');
      assert.equal(snapshot.expectedVariants, 2);
    });

    it('converges two store instances writing the same session from different processes', () => {
      const server = createLiveSessionStore({ cwd: tmp, sessionId: 'two-writers' });
      const publisher = createLiveSessionStore({ cwd: tmp, sessionId: 'two-writers' });

      server.appendEvent({ type: 'generate', id: 'two-writers', count: 3, element: { classes: ['hero'] } });
      // The publisher's first append must see the server's event, not start
      // from an empty snapshot with sequence 1 again.
      publisher.appendEvent({ type: 'checkpoint', id: 'two-writers', revision: 2, phase: 'cycling', arrivedVariants: 1 });
      server.appendEvent({ type: 'variant_mounted', id: 'two-writers', variant: 1 });
      publisher.appendEvent({ type: 'variants_ready', id: 'two-writers', file: 'src/App.jsx', arrivedVariants: 3 });

      const fromServer = server.getSnapshot('two-writers');
      const fromPublisher = publisher.getSnapshot('two-writers');
      assert.deepEqual({ ...fromServer, updatedAt: null }, { ...fromPublisher, updatedAt: null });
      assert.equal(fromServer.arrivedVariants, 3);
      assert.equal(fromServer.expectedVariants, 3);
      assert.deepEqual(fromServer.mountedVariants, [1]);

      const seqs = readFileSync(join(getLiveSessionsDir(tmp), 'two-writers.jsonl'), 'utf-8')
        .split('\n')
        .filter((line) => line.trim())
        .map((line) => JSON.parse(line).seq);
      assert.deepEqual(
        seqs,
        [1, 2, 3, 4],
        'event=live_session_store.seq_collision actor=publisher operation=append_event risk=two_processes_reuse_sequence_numbers actual=' + JSON.stringify(seqs),
      );
    });

    it('re-derives when another process appends behind a cached reader', () => {
      const reader = createLiveSessionStore({ cwd: tmp, sessionId: 'external-append' });
      const writer = createLiveSessionStore({ cwd: tmp, sessionId: 'external-append' });
      writer.appendEvent({ type: 'generate', id: 'external-append', count: 3, element: { classes: ['hero'] } });
      assert.equal(reader.getSnapshot('external-append').phase, 'generate_requested');

      writer.appendEvent({ type: 'accept', id: 'external-append', variantId: '2' });
      assert.equal(
        reader.getSnapshot('external-append').phase,
        'accept_requested',
        'event=live_session_store.cache_staleness actor=agent operation=get_snapshot risk=reader_serves_pre_accept_state',
      );
      assert.equal(reader.getSnapshot('external-append').visibleVariant, 2);
    });

    it('flushes the snapshot file on demand without appending an event', () => {
      const store = createLiveSessionStore({ cwd: tmp, sessionId: 'flushable' });
      store.appendEvent({ type: 'generate', id: 'flushable', count: 1, element: { classes: ['hero'] } });
      const snapshotPath = join(getLiveSessionsDir(tmp), 'flushable.snapshot.json');
      rmSync(snapshotPath);

      const flushed = createLiveSessionStore({ cwd: tmp }).flush('flushable');
      assert.equal(flushed.phase, 'generate_requested');
      const onDisk = JSON.parse(readFileSync(snapshotPath, 'utf-8'));
      assert.equal(onDisk.phase, 'generate_requested');
      const journalBytes = statSync(join(getLiveSessionsDir(tmp), 'flushable.jsonl')).size;
      assert.equal(onDisk.__journalBytes, journalBytes);
    });

    it('keeps journal bookkeeping out of the snapshot it hands callers', () => {
      const store = createLiveSessionStore({ cwd: tmp, sessionId: 'no-meta' });
      const returned = store.appendEvent({ type: 'generate', id: 'no-meta', count: 1, element: { classes: ['hero'] } });
      assert.equal(returned.__journalBytes, undefined);
      assert.equal(returned.__nextSeq, undefined);

      const hydrated = createLiveSessionStore({ cwd: tmp }).getSnapshot('no-meta');
      assert.equal(hydrated.__journalBytes, undefined);
      assert.equal(hydrated.__nextSeq, undefined);
    });
  });

  describe('render truth', () => {
    function seedPublishedSession(store, id) {
      store.appendEvent({ type: 'generate', id, count: 3, element: { classes: ['hero'] } });
      store.appendEvent({ type: 'variants_ready', id, file: 'src/App.svelte' });
    }

    it('starts a published cycle as pending, before any browser acknowledgement', () => {
      const store = createLiveSessionStore({ cwd: tmp, sessionId: 'render-pending' });
      seedPublishedSession(store, 'render-pending');

      const snapshot = store.getSnapshot('render-pending');
      assert.equal(
        snapshot.arrivedVariants,
        3,
        'the published-variant backfill stays for compatibility',
      );
      assert.equal(
        snapshot.renderState,
        'pending',
        'event=live_session_store.render_truth actor=agent operation=publish risk=published_mistaken_for_rendered expected=pending actual=' + snapshot.renderState,
      );
      assert.deepEqual(snapshot.mountedVariants, []);
      assert.deepEqual(snapshot.mountFailures, []);
    });

    it('records distinct mounted variants and flips renderState to mounted', () => {
      const store = createLiveSessionStore({ cwd: tmp, sessionId: 'render-mounted' });
      seedPublishedSession(store, 'render-mounted');
      store.appendEvent({ type: 'variant_mounted', id: 'render-mounted', variant: 2 });
      store.appendEvent({ type: 'variant_mounted', id: 'render-mounted', variant: 2 });
      store.appendEvent({ type: 'variant_mounted', id: 'render-mounted', variant: 1 });

      const snapshot = store.getSnapshot('render-mounted');
      assert.deepEqual(snapshot.mountedVariants, [1, 2]);
      assert.equal(snapshot.renderState, 'mounted');
      assert.equal(snapshot.diagnostics.length, 0, 'mount acks are known event types');
    });

    it('reports failed while nothing has mounted, and caps the failure history at five', () => {
      const store = createLiveSessionStore({ cwd: tmp, sessionId: 'render-failed' });
      seedPublishedSession(store, 'render-failed');
      for (let i = 1; i <= 7; i++) {
        store.appendEvent({
          type: 'variant_mount_failed',
          id: 'render-failed',
          variant: i,
          url: '/preview/v' + i + '.svelte',
          error: 'import failed ' + i,
          at: 1000 + i,
        });
      }

      const snapshot = store.getSnapshot('render-failed');
      assert.equal(snapshot.renderState, 'failed');
      assert.equal(snapshot.mountFailures.length, 5);
      assert.deepEqual(
        snapshot.mountFailures.map((failure) => failure.variant),
        [3, 4, 5, 6, 7],
        'the newest failures are the ones worth keeping',
      );
      assert.deepEqual(snapshot.mountFailures[4], {
        variant: 7,
        url: '/preview/v7.svelte',
        error: 'import failed 7',
        at: 1007,
      });
    });

    it('lets one successful mount outrank earlier failures', () => {
      const store = createLiveSessionStore({ cwd: tmp, sessionId: 'render-mixed' });
      seedPublishedSession(store, 'render-mixed');
      store.appendEvent({
        type: 'variant_mount_failed', id: 'render-mixed', variant: 2, url: '/v2.svelte', error: 'boom',
      });
      assert.equal(store.getSnapshot('render-mixed').renderState, 'failed');
      store.appendEvent({ type: 'variant_mounted', id: 'render-mixed', variant: 1 });

      const snapshot = store.getSnapshot('render-mixed');
      assert.equal(snapshot.renderState, 'mounted');
      assert.equal(snapshot.mountFailures.length, 1, 'the failure stays on the record');
    });

    it('resets render truth when a new generate starts the next cycle', () => {
      const store = createLiveSessionStore({ cwd: tmp, sessionId: 'render-reset' });
      seedPublishedSession(store, 'render-reset');
      store.appendEvent({ type: 'variant_mounted', id: 'render-reset', variant: 1 });
      store.appendEvent({
        type: 'variant_mount_failed', id: 'render-reset', variant: 3, url: '/v3.svelte', error: 'boom',
      });
      store.appendEvent({ type: 'generate', id: 'render-reset', count: 2, element: { classes: ['hero'] } });

      const snapshot = store.getSnapshot('render-reset');
      assert.deepEqual(snapshot.mountedVariants, []);
      assert.deepEqual(snapshot.mountFailures, []);
      assert.equal(snapshot.renderState, null);
    });

    it('survives a journal replay in a fresh process', () => {
      const store = createLiveSessionStore({ cwd: tmp, sessionId: 'render-replay' });
      seedPublishedSession(store, 'render-replay');
      store.appendEvent({
        type: 'variant_mount_failed', id: 'render-replay', variant: 1, url: '/v1.svelte', error: 'boom',
      });

      const restarted = createLiveSessionStore({ cwd: tmp, sessionId: 'render-replay' });
      const snapshot = restarted.getSnapshot('render-replay');
      assert.equal(snapshot.renderState, 'failed');
      assert.equal(snapshot.mountFailures[0].url, '/v1.svelte');
    });

    it('diagnoses a mount ack with no usable variant instead of trusting it', () => {
      const store = createLiveSessionStore({ cwd: tmp, sessionId: 'render-bad' });
      seedPublishedSession(store, 'render-bad');
      store.appendEvent({ type: 'variant_mounted', id: 'render-bad', variant: 0 });

      const snapshot = store.getSnapshot('render-bad');
      assert.deepEqual(snapshot.mountedVariants, []);
      assert.equal(snapshot.renderState, 'pending');
      assert.equal(snapshot.diagnostics.some((d) => d.error === 'malformed_mount_ack'), true);
    });
  });
});

describe('review regressions: durable mount failures', () => {
  it('variant_mount_failed survives a helper restart as the pending event', () => {
    const tmp = mkdtempSync(join(tmpdir(), 'impeccable-store-mountfail-'));
    try {
      const store = createLiveSessionStore({ cwd: tmp });
      store.appendEvent({ type: 'generate', id: 'mf123456', count: 3, pageUrl: '/', element: { tagName: 'h1' } });
      store.appendEvent({ type: 'agent_done', id: 'mf123456' });
      store.appendEvent({ type: 'variant_mount_failed', id: 'mf123456', variant: 2, url: 'http://x/v2.svelte', error: 'boom' });

      // A second store instance = the restarted helper.
      const restarted = createLiveSessionStore({ cwd: tmp });
      const snapshot = restarted.getSnapshot('mf123456');
      assert.equal(snapshot.pendingEvent?.type, 'variant_mount_failed');
      assert.equal(snapshot.pendingEvent?.variant, 2);

      // The repair reply retires it.
      restarted.appendEvent({ type: 'agent_done', id: 'mf123456', sourceEventType: 'variant_mount_failed' });
      assert.equal(restarted.getSnapshot('mf123456').pendingEvent, null);
    } finally {
      rmSync(tmp, { recursive: true, force: true });
    }
  });

  it('a mount failure does not clobber a still-pending generate', () => {
    const tmp = mkdtempSync(join(tmpdir(), 'impeccable-store-mountfail2-'));
    try {
      const store = createLiveSessionStore({ cwd: tmp });
      store.appendEvent({ type: 'generate', id: 'mf223456', count: 3, pageUrl: '/', element: { tagName: 'h1' } });
      store.appendEvent({ type: 'variant_mount_failed', id: 'mf223456', variant: 1, url: 'http://x/v1.svelte', error: 'early' });
      assert.equal(store.getSnapshot('mf223456').pendingEvent?.type, 'generate');
    } finally {
      rmSync(tmp, { recursive: true, force: true });
    }
  });
});
