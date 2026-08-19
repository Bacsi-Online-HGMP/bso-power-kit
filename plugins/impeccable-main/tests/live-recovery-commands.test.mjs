import { describe, it } from 'node:test';
import assert from 'node:assert/strict';
import { mkdtempSync, readFileSync, readdirSync, rmSync, statSync } from 'node:fs';
import { join } from 'node:path';
import { tmpdir } from 'node:os';
import { execFileSync } from 'node:child_process';
import { createLiveSessionStore } from '../skill/scripts/live/session-store.mjs';

const REPO_ROOT = process.cwd();
const STATUS_SCRIPT = join(REPO_ROOT, 'skill/scripts/live-status.mjs');
const RESUME_SCRIPT = join(REPO_ROOT, 'skill/scripts/live-resume.mjs');
const COMPLETE_SCRIPT = join(REPO_ROOT, 'skill/scripts/live-complete.mjs');

function withTempProject(fn) {
  const cwd = mkdtempSync(join(tmpdir(), 'impeccable-live-recovery-'));
  try { return fn(cwd); }
  finally { rmSync(cwd, { recursive: true, force: true }); }
}

function snapshotDir(dir) {
  return readdirSync(dir).sort().map((name) => {
    const filePath = join(dir, name);
    return { name, mtimeMs: statSync(filePath).mtimeMs, body: readFileSync(filePath, 'utf-8') };
  });
}

function runJson(script, args, cwd) {
  const out = execFileSync(process.execPath, [script, ...args], { cwd, encoding: 'utf-8' });
  return JSON.parse(out);
}

describe('live recovery CLI commands', () => {
  it('prints active durable session status without a running helper server', () => withTempProject((cwd) => {
    const store = createLiveSessionStore({ cwd });
    store.appendEvent({ type: 'generate', id: 'cli-recover-1', action: 'impeccable', count: 3, pageUrl: '/', element: { outerHTML: '<button>Go</button>' } });

    const status = runJson(STATUS_SCRIPT, [], cwd);
    assert.equal(status.liveServer, null);
    assert.equal(status.activeSessions.length, 1);
    assert.equal(status.activeSessions[0].id, 'cli-recover-1');
    assert.match(status.recoveryHint, /Start live-server/);
  }));

  it('leaves every session file untouched while reporting status', () => withTempProject((cwd) => {
    const store = createLiveSessionStore({ cwd });
    store.appendEvent({ type: 'generate', id: 'cli-readonly-1', action: 'impeccable', count: 2, pageUrl: '/', element: { outerHTML: '<section>Hero</section>' } });
    store.appendEvent({ type: 'variants_ready', id: 'cli-readonly-1', file: 'src/App.jsx', arrivedVariants: 2 });

    const sessionsDir = join(cwd, '.impeccable', 'live', 'sessions');
    const before = snapshotDir(sessionsDir);

    // Both commands run in their own process against a session a live server
    // may still own. Reporting on it must not rewrite it.
    runJson(STATUS_SCRIPT, [], cwd);
    runJson(RESUME_SCRIPT, ['--id', 'cli-readonly-1'], cwd);

    assert.deepEqual(
      snapshotDir(sessionsDir),
      before,
      'event=live_recovery.read_mutates_state actor=agent operation=status_and_resume risk=reporting_rewrites_session_files',
    );
  }));

  it('resumes the pending event and reports the next safe agent action', () => withTempProject((cwd) => {
    const store = createLiveSessionStore({ cwd });
    store.appendEvent({ type: 'generate', id: 'cli-recover-2', action: 'impeccable', count: 2, pageUrl: '/', element: { outerHTML: '<section>Hero</section>' } });

    const resume = runJson(RESUME_SCRIPT, ['--id', 'cli-recover-2'], cwd);
    assert.equal(resume.active, true);
    assert.equal(resume.pendingEvent.type, 'generate');
    assert.match(
      resume.nextAction,
      /live-poll\.mjs/,
      'event=live_resume.next_action actor=agent operation=recover_session risk=agent_has_state_but_no_next_step expected=live-poll.mjs actual=' + resume.nextAction,
    );
  }));

  it('resumes manual Apply with the structured reply action, not a plain ack', () => withTempProject((cwd) => {
    const store = createLiveSessionStore({ cwd });
    store.appendEvent({
      type: 'manual_edit_apply',
      id: 'manual-recover-1',
      pageUrl: '/',
      chunk: { index: 3, total: 3, opCount: 2, totalOpCount: 8 },
      batch: {
        entries: [{
          id: 'entry-a',
          ops: [{
            ref: 'body>p:nth-of-type(1)',
            originalText: 'Old',
            newText: 'New',
            sourceHint: { file: 'src/App.jsx', line: 12 },
          }],
        }],
        candidates: [],
      },
    });

    const resume = runJson(RESUME_SCRIPT, ['--id', 'manual-recover-1'], cwd);
    assert.equal(resume.active, true);
    assert.equal(resume.pendingEvent.type, 'manual_edit_apply');
    assert.equal(resume.snapshot.phase, 'manual_edit_apply_requested');
    assert.match(resume.nextAction, /--reply manual-recover-1 done --data '<json>'/);
    assert.match(resume.nextAction, /Polling only leases this work item; it does not commit source edits/);
    assert.match(resume.nextAction, /Do not run live-commit-manual-edits\.mjs/);
    assert.match(resume.nextAction, /chunk 3\/3/);
    assert.match(resume.nextAction, /likely files: src\/App\.jsx/);
    assert.doesNotMatch(resume.nextAction, /acknowledge with live-poll\.mjs --reply manual-recover-1 done\./);

    const status = runJson(STATUS_SCRIPT, [], cwd);
    assert.match(status.recoveryHint, /--reply manual-recover-1 done --data '<json>'/);
    assert.match(status.recoveryHint, /Do not poll again before replying/);
  }));

  it('resumes carbonize-required sessions with a cleanup-specific next action', () => withTempProject((cwd) => {
    const store = createLiveSessionStore({ cwd });
    store.appendEvent({ type: 'accept', id: 'cli-carbonize-1', variantId: '1' });
    store.appendEvent({ type: 'agent_done', id: 'cli-carbonize-1', file: 'src/App.jsx', carbonize: true });

    const resume = runJson(RESUME_SCRIPT, ['--id', 'cli-carbonize-1'], cwd);
    assert.equal(resume.active, true);
    assert.equal(resume.snapshot.phase, 'carbonize_required');
    assert.match(
      resume.nextAction,
      /Finish carbonize cleanup in src\/App\.jsx/,
      'event=live_resume.carbonize_next_action actor=agent operation=recover_carbonize risk=carbonize_cleanup_hidden_after_accept expected=cleanup-specific action actual=' + resume.nextAction,
    );
  }));

  it('reports render truth so published is never read as rendered', () => withTempProject((cwd) => {
    const store = createLiveSessionStore({ cwd });
    store.appendEvent({ type: 'generate', id: 'cli-render-1', action: 'impeccable', count: 3, pageUrl: '/', element: { outerHTML: '<section>Hero</section>' } });
    store.appendEvent({ type: 'agent_done', id: 'cli-render-1', file: 'src/App.svelte' });
    store.appendEvent({ type: 'variant_mounted', id: 'cli-render-1', variant: 1 });

    const resume = runJson(RESUME_SCRIPT, ['--id', 'cli-render-1'], cwd);
    assert.equal(resume.render.renderState, 'mounted');
    assert.deepEqual(resume.render.mountedVariants, [1]);
    assert.deepEqual(resume.render.mountFailures, []);

    const status = runJson(STATUS_SCRIPT, [], cwd);
    assert.equal(status.render[0].renderState, 'mounted');
    assert.deepEqual(status.render[0].mountedVariants, [1]);
  }));

  it('turns a browser mount failure into an actionable next step', () => withTempProject((cwd) => {
    const store = createLiveSessionStore({ cwd });
    store.appendEvent({ type: 'generate', id: 'cli-render-2', action: 'impeccable', count: 3, pageUrl: '/', element: { outerHTML: '<section>Hero</section>' } });
    store.appendEvent({ type: 'agent_done', id: 'cli-render-2', file: 'src/App.svelte' });
    store.appendEvent({
      type: 'variant_mount_failed',
      id: 'cli-render-2',
      variant: 2,
      url: '/preview/v2.svelte',
      error: 'Failed to fetch dynamically imported module',
    });

    const resume = runJson(RESUME_SCRIPT, ['--id', 'cli-render-2'], cwd);
    assert.equal(resume.render.renderState, 'failed');
    assert.match(
      resume.nextAction,
      /failed to mount variant 2 from \/preview\/v2\.svelte/,
      'event=live_resume.mount_failure_action actor=agent operation=recover_session risk=agent_thinks_variants_are_on_screen expected=named failing variant and url actual=' + resume.nextAction,
    );
    assert.match(resume.nextAction, /variant_mount_failed/);
    assert.match(resume.nextAction, /--reply cli-render-2 done --file/);

    const status = runJson(STATUS_SCRIPT, [], cwd);
    assert.match(status.recoveryHint, /failed to mount variant 2/);
  }));

  it('marks a session completed through the canonical completion command', () => withTempProject((cwd) => {
    const store = createLiveSessionStore({ cwd });
    store.appendEvent({ type: 'generate', id: 'cli-recover-3', action: 'impeccable', count: 1, pageUrl: '/', element: { outerHTML: '<p>Copy</p>' } });

    const completed = runJson(COMPLETE_SCRIPT, ['--id', 'cli-recover-3'], cwd);
    assert.equal(completed.ok, true);
    assert.equal(completed.phase, 'completed');

    const status = runJson(STATUS_SCRIPT, [], cwd);
    assert.deepEqual(status.activeSessions, []);
  }));
});
