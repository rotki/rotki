import type { OrchestratorOptions, TaskOrchestrator } from './api';
import { err, ok, type Result } from 'plainfp/result';
import { isTerminalStatus } from '../status';
import {
  type Activity,
  type ActivityId,
  activityIdHasPrefix,
  type ActivityKind,
  type ActivityStatus,
  type ActivitySteps,
  type CompletionRecord,
  type GroupId,
  makeActivityId,
  ActivityStatus as Status,
  type WorkStatus,
} from '../types';
import { AlreadyTerminal, type ControlError, NotCancellable, NotFound, NotRerunnable } from './errors';
import { dropCompletions, markStaleAfter, recordCompletion, recordSettlement } from './ledger';
import { endedIncomplete, liveChildrenOf, runActivity, terminalStatus } from './lifecycle';
import { aggregateStatus, childProgress, projectActivity, statusForId } from './projection';
import { allRulesPass, DEFAULT_RULES } from './rules';
import { createScheduler } from './scheduler';
import { type ActivitySpec, DEFAULT_LANE, DEFAULT_PRIORITY, type ReportProgress, type StaleAfterEdge } from './spec';

interface ActivityRecord {
  readonly spec: ActivitySpec;
  status: ActivityStatus;
  steps?: ActivitySteps;
  startedAt?: number;
  /** Set when the user cancelled a running activity; forces the terminal status to CANCELLED. */
  cancelRequested: boolean;
  /** Guards the spec's `cleanup` to fire once per run-cycle; re-armed on re-run. */
  cleanedUp: boolean;
}

/**
 * The execution spine of the Task Center. Owns the queue and lifecycle of every *native*
 * activity: schedules it (lanes + caps + dependency/rule gating via {@link createScheduler}),
 * runs it as a plainfp {@link ResultAsync} (timeout/retry), maps the outcome to a terminal
 * status, and emits on every change. Framework-agnostic — `use-task-orchestrator` wraps it in
 * a reactive snapshot, and the floor/bridged activities are merged in the reactive shell, not
 * here.
 */
export function createTaskOrchestrator(options: OrchestratorOptions = {}): TaskOrchestrator {
  const rules = options.rules ?? DEFAULT_RULES;
  const now = options.now ?? ((): number => Date.now());
  const records = new Map<ActivityId, ActivityRecord>();
  /** Durable per-id completion memory — survives `clearTerminal`; the freshness backbone. */
  const ledger = new Map<ActivityId, CompletionRecord>();
  const listeners = new Set<() => void>();
  /**
   * Consumer id → what invalidates it. Kept separately from `records` so an edge survives
   * `clearTerminal` pruning the consumer's finished record: the ledger entry it invalidates
   * outlives that record, so the edge has to as well.
   */
  const staleEdges = new Map<ActivityId, readonly StaleAfterEdge[]>();
  const scheduler = createScheduler(options.caps, options.defaultCap, options.laneFamilies, options.laneFamilyActive);

  function emit(): void {
    for (const listener of listeners)
      listener();
  }

  /**
   * The single funnel for terminal transitions: set the status, write the completion ledger,
   * then emit. Guarded against post-reset orphans: an in-flight run settling after the record was
   * dropped writes nothing.
   *
   * The guard compares record *identity*, not just the presence of the id. `submitTask` resolves
   * its caller a tick before the run reaches here, so a caller that awaits and immediately
   * re-submits the same id replaces `records[id]` while the old run is still in flight. Testing
   * `has(id)` let that stale run settle the *new* record's id: it wrote a COMPLETE ledger entry
   * and fired `markStaleAfter` for work that had barely started, so `everCompleted` read true and
   * downstream consumers were invalidated off a run that was not theirs.
   */
  function settleTerminal(record: ActivityRecord, status: ActivityStatus): void {
    if (records.get(record.spec.id) !== record)
      return;

    record.status = status;
    recordSettlement(record.spec.id, record.spec.kind, status, now(), ledger);
    // Tear down producer side resources once — settleTerminal may run twice (cancel then the
    // aborted run resolving), so the flag keeps `cleanup` from double-firing.
    if (!record.cleanedUp) {
      record.cleanedUp = true;
      record.spec.cleanup?.();
    }
    emit();

    if (status === Status.COMPLETE && markStaleAfter(record.spec.id, staleEdges, ledger))
      emit();

    // 🔴 An activity that ends without completing takes its subtree with it — cancelled, failed or
    // skipped alike. Hanging the cascade off the settle rather than off `cancel` is what makes it
    // one rule instead of two: a parent that fails mid-flight orphans its queued children exactly
    // the way an explicit cancel used to.
    //
    // ⭐ Recursion terminates on a malformed parent cycle without a seen-set, because `status` is
    // already terminal by the time this runs, so a node reached a second time is skipped.
    if (status !== Status.COMPLETE)
      cancelDescendantsOf(record.spec.id);
  }

  /**
   * Cancel everything beneath `id`. Each child settles through {@link settleTerminal}, which walks
   * its own children in turn, so the whole subtree comes down from one call.
   *
   * ⚠️ A child that cannot be cancelled never stops the walk. A RUNNING node with no cancel handle
   * is left alone and its siblings still come down; abandoning the rest of the subtree over one
   * such node is the bug this fixes, not a safety property.
   */
  function cancelDescendantsOf(id: ActivityId): void {
    for (const child of liveChildrenOf(records, id))
      cancelOne(child);
  }

  /**
   * Deliberately does NOT run {@link markStaleAfter}: a restore is not a fresh production of data,
   * and invalidating consumers off it would turn "we already have this" into a refetch of
   * everything downstream.
   */
  function markCompleted(kind: ActivityKind, ...parts: (string | number)[]): void {
    recordCompletion(makeActivityId(kind, ...parts), kind, now(), ledger);
    emit();
  }

  /**
   * Live records are untouched, matching {@link markStaleAfter}: an in-flight refresh keeps
   * running and writes a fresh entry when it settles.
   */
  function invalidate(kind: ActivityKind, ...parts: (string | number)[]): void {
    if (dropCompletions(kind, parts, ledger))
      emit();
  }

  function reportProgress(id: ActivityId, steps: ActivitySteps): void {
    const record = records.get(id);
    if (record?.status === Status.RUNNING) {
      record.steps = steps;
      emit();
    }
  }

  function reportProgressByPrefix(steps: ActivitySteps, kind: ActivityKind, ...parts: (string | number)[]): void {
    for (const [id, record] of records.entries()) {
      if (record.status === Status.RUNNING && activityIdHasPrefix(id, kind, ...parts))
        reportProgress(id, steps);
    }
  }

  const project = (record: ActivityRecord, children?: Map<ActivityId, ActivitySteps>): Activity =>
    projectActivity(record, children?.get(record.spec.id));

  function snapshot(): Activity[] {
    const children = childProgress(records);
    return Array.from(records.values(), record => project(record, children));
  }

  function statusOf(kind: ActivityKind, ...parts: (string | number)[]): WorkStatus {
    return parts.length > 0
      ? statusForId(records, ledger, makeActivityId(kind, ...parts))
      : aggregateStatus(records, ledger, (_id, activityKind) => activityKind === kind);
  }

  /**
   * Aggregate {@link WorkStatus} over every activity whose id extends `kind:parts` — the coarse
   * read for producers that submit one activity per request (see {@link activityIdHasPrefix}).
   * With no parts this is identical to `statusOf(kind)`.
   */
  function statusOfPrefix(kind: ActivityKind, ...parts: (string | number)[]): WorkStatus {
    return aggregateStatus(records, ledger, id => activityIdHasPrefix(id, kind, ...parts));
  }

  function eligible(record: ActivityRecord): boolean {
    if (record.status !== Status.PENDING || record.cancelRequested)
      return false;

    // A child never starts before the activity it belongs to. A pre-submitted tree is queued all
    // at once, so without this a chain's accounts could run while the chain itself is still
    // PENDING — the tree would show a parent yet to start above children already working. An
    // unknown parent does not gate, so a child can never be wedged by a parent that never existed.
    if (record.spec.parent !== undefined) {
      const parent = records.get(record.spec.parent);
      if (parent?.status === Status.PENDING)
        return false;

      // ⛔ No check for a parent that ended incomplete belongs here. Refusing is not settling, so a
      // child nothing will ever make eligible would sit PENDING for the life of the process,
      // holding its caller's await open with it. `settleTerminal` cancels the subtree and `submit`
      // settles a late arrival — both *end* the child rather than leaving it queued forever.
    }

    const depsSatisfied = (record.spec.deps ?? []).every((depId) => {
      const dep = records.get(depId);
      return dep === undefined || isTerminalStatus(dep.status);
    });
    if (!depsSatisfied)
      return false;

    return allRulesPass(rules, project(record), snapshot());
  }

  async function execute(record: ActivityRecord): Promise<void> {
    record.status = Status.RUNNING;
    record.startedAt = now();
    emit();

    const report: ReportProgress = steps => reportProgress(record.spec.id, steps);
    const outcome = await runActivity(record.spec, report);

    settleTerminal(record, terminalStatus(record.cancelRequested, outcome));
  }

  function schedule(record: ActivityRecord): void {
    scheduler.submit({
      eligible: () => eligible(record),
      id: record.spec.id,
      lane: record.spec.lane ?? DEFAULT_LANE,
      priority: record.spec.priority ?? DEFAULT_PRIORITY,
      run: async () => execute(record),
    });
  }

  function submit<T>(spec: ActivitySpec<T>): ActivityId {
    // Re-submitting an id whose previous run is still in flight abandons that run: `settleTerminal`
    // will refuse it at the identity guard, so this is the last chance to release what it holds.
    // Without it the identity guard would trade a corrupted ledger for a leaked producer resource.
    const superseded = records.get(spec.id);
    if (superseded && !isTerminalStatus(superseded.status) && !superseded.cleanedUp) {
      superseded.cleanedUp = true;
      superseded.spec.cleanup?.();
    }

    const record: ActivityRecord = { cancelRequested: false, cleanedUp: false, spec, status: Status.PENDING };
    records.set(spec.id, record);
    if (spec.staleAfter?.length)
      staleEdges.set(spec.id, spec.staleAfter);

    // A child arriving after its parent already ended without completing belongs to a subtree that
    // is gone, so it is settled here rather than scheduled. `eligible` would refuse to start it
    // either way — but refusing is not settling, and a record nothing will ever make eligible sits
    // PENDING for the life of the process, holding its caller's await open with it.
    const parent = spec.parent === undefined ? undefined : records.get(spec.parent);
    if (parent !== undefined && endedIncomplete(parent)) {
      settleTerminal(record, Status.CANCELLED);
      return spec.id;
    }

    schedule(record);
    emit();
    return spec.id;
  }

  /** One node's cancellation. No `pump` — {@link cancel} pumps once for the whole subtree. */
  function cancelOne(record: ActivityRecord): Result<void, ControlError> {
    const id = record.spec.id;
    if (isTerminalStatus(record.status))
      return err(AlreadyTerminal({ id }));

    if (record.status === Status.PENDING) {
      scheduler.drop(id);
      settleTerminal(record, Status.CANCELLED);
      return ok(undefined);
    }

    // RUNNING: a cancel handle is required to interrupt in-flight work.
    if (!record.spec.cancel)
      return err(NotCancellable({ id }));
    record.cancelRequested = true;
    record.spec.cancel();
    // Reflect the cancellation immediately; `cancelRequested` keeps it CANCELLED even if the
    // aborting task later settles ok. The scheduler slot frees once `run` actually resolves.
    settleTerminal(record, Status.CANCELLED);
    return ok(undefined);
  }

  /**
   * Cancel an activity **and everything beneath it**. "Stop this refresh" is one act.
   *
   * 🔴 Cancelling a parent alone settled its row and stopped nothing: the handle every native spec
   * carries only aborts that activity's own backend task, which an umbrella never has, so the row
   * went CANCELLED and vanished while its children kept running — and queued ones still started,
   * because `eligible` only refused a child whose parent was still PENDING.
   *
   * ⭐ No new cancel handle is needed anywhere. Once the children settle, the parent's `Promise.all`
   * resolves on its own and `cancelRequested` maps that outcome to CANCELLED.
   *
   * The walk itself lives in {@link settleTerminal}, so this is only the root's own cancellation:
   * every path that ends an activity incomplete brings its subtree down, not just this one.
   */
  function cancel(id: ActivityId): Result<void, ControlError> {
    const record = records.get(id);
    if (!record)
      return err(NotFound({ id }));

    const outcome = cancelOne(record);
    // Once, for the whole subtree: a cancelled dep may unblock dependents / rules.
    scheduler.pump();
    return outcome;
  }

  function cancelMatching(predicate: (record: ActivityRecord) => boolean): void {
    for (const record of records.values()) {
      if (!isTerminalStatus(record.status) && predicate(record))
        cancel(record.spec.id);
    }
  }

  function rerun(id: ActivityId): Result<void, ControlError> {
    const record = records.get(id);
    if (!record)
      return err(NotFound({ id }));
    if (!record.spec.rerunnable || !isTerminalStatus(record.status))
      return err(NotRerunnable({ id }));

    record.status = Status.PENDING;
    record.steps = undefined;
    record.startedAt = undefined;
    record.cancelRequested = false;
    record.cleanedUp = false;
    schedule(record);
    emit();
    return ok(undefined);
  }

  return {
    cancel,
    cancelAll: () => cancelMatching(() => true),
    cancelByKind: (kind: ActivityKind) => cancelMatching(record => record.spec.kind === kind),
    cancelByPrefix: (kind: ActivityKind, ...parts: (string | number)[]) =>
      cancelMatching(record => activityIdHasPrefix(record.spec.id, kind, ...parts)),
    cancelGroup: (group: GroupId) => cancelMatching(record => record.spec.group === group),
    clearTerminal(): void {
      for (const [id, record] of records) {
        if (isTerminalStatus(record.status))
          records.delete(id);
      }
      emit();
    },
    invalidate,
    markCompleted,
    onChange(listener: () => void): () => void {
      listeners.add(listener);
      return () => listeners.delete(listener);
    },
    reportProgress,
    reportProgressByPrefix,
    rerun,
    reset(): void {
      // Tear down live producers before dropping their records. Clearing `records` first would
      // make `settleTerminal` return at its identity guard when the abandoned run resolves, so
      // `cleanup` never fired: a P&L report generated across a logout kept its 2s `getProgress()`
      // poll hitting the backend for a session that had ended. Settled here rather than through
      // `settleTerminal` because the ledger it would write is cleared on the next line anyway.
      for (const record of records.values()) {
        if (isTerminalStatus(record.status) || record.cleanedUp)
          continue;
        record.status = Status.CANCELLED;
        record.cleanedUp = true;
        record.spec.cleanup?.();
      }
      // ⚠️ Emit while the cancelled records are still in the map. A caller awaiting `submitTask`
      // is released by a resolver that looks its activity up in the snapshot and settles it when
      // it reads terminal; clearing first makes that lookup miss, so the caller never settles.
      // Worse, the id is held in `inflight` until it settles, so it stays poisoned for the life of
      // the process and every later submit dedups onto a promise that can no longer resolve. In
      // the app that stalls `fetchCached()` on its first await after a re-login, so accounts are
      // never fetched and the session sits on a spinner with nothing running.
      emit();

      records.clear();
      ledger.clear();
      staleEdges.clear();
      scheduler.clear();
      emit();
    },
    snapshot,
    statusOf,
    statusOfPrefix,
    submit,
  };
}
