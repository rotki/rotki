import { INDETERMINATE, isTerminalStatus, percentageFromSteps } from '../status';
import { type Activity, type ActivityId, type ActivityKind, ActivitySourceType, type ActivityStatus, type ActivitySteps, type CompletionRecord, ActivityStatus as Status, type WorkStatus } from '../types';

/**
 * The status projection: how live records and the completion ledger collapse into a
 * {@link WorkStatus}. Pure and orchestrator-agnostic — it reads only the two maps it is handed,
 * which keeps the orchestrator module focused on lifecycle and scheduling.
 *
 * @packageDocumentation
 */

/**
 * The subset of an activity record this projection needs — structurally satisfied by the
 * orchestrator's `ActivityRecord`, so no adapter or per-call remapping is required.
 */
export interface ProjectedRecord {
  readonly status: ActivityStatus;
  readonly spec: { readonly kind: ActivityKind };
}

/**
 * Selects which activities an aggregate covers. Receives both the id and the declared kind so a
 * whole-kind aggregate can match on the kind while a prefix aggregate matches on the id.
 */
export type IdMatcher = (id: ActivityId, kind: ActivityKind) => boolean;

function liveness(
  records: ReadonlyMap<ActivityId, ProjectedRecord>,
  matches: IdMatcher,
): { running: boolean; pending: boolean } {
  let running = false;
  let pending = false;
  for (const [id, record] of records) {
    if (!matches(id, record.spec.kind))
      continue;
    running ||= record.status === Status.RUNNING;
    pending ||= record.status === Status.PENDING;
  }
  return { pending, running };
}

function freshness(
  ledger: ReadonlyMap<ActivityId, CompletionRecord>,
  matches: IdMatcher,
): { lastCompletedAt?: number; lastOutcome?: ActivityStatus } {
  let lastCompletedAt = Number.NEGATIVE_INFINITY;
  let lastSettledAt = Number.NEGATIVE_INFINITY;
  let lastOutcome: ActivityStatus | undefined;
  for (const [id, entry] of ledger) {
    if (!matches(id, entry.kind))
      continue;
    if ((entry.lastSuccessAt ?? Number.NEGATIVE_INFINITY) > lastCompletedAt)
      lastCompletedAt = entry.lastSuccessAt ?? lastCompletedAt;
    if (entry.lastSettledAt > lastSettledAt) {
      lastSettledAt = entry.lastSettledAt;
      lastOutcome = entry.lastOutcome;
    }
  }
  return { lastCompletedAt: Number.isFinite(lastCompletedAt) ? lastCompletedAt : undefined, lastOutcome };
}

/** Liveness + freshness folded over every activity the matcher selects. */
export function aggregateStatus(
  records: ReadonlyMap<ActivityId, ProjectedRecord>,
  ledger: ReadonlyMap<ActivityId, CompletionRecord>,
  matches: IdMatcher,
): WorkStatus {
  const { pending, running } = liveness(records, matches);
  const { lastCompletedAt, lastOutcome } = freshness(ledger, matches);

  return {
    active: running || pending,
    everCompleted: lastCompletedAt !== undefined,
    lastCompletedAt,
    lastOutcome,
    pending,
    running,
  };
}

/** Liveness + freshness for one exact id. */
export function statusForId(
  records: ReadonlyMap<ActivityId, ProjectedRecord>,
  ledger: ReadonlyMap<ActivityId, CompletionRecord>,
  id: ActivityId,
): WorkStatus {
  const record = records.get(id);
  const entry = ledger.get(id);
  const running = record?.status === Status.RUNNING;
  const pending = record?.status === Status.PENDING;
  return {
    active: running || pending,
    everCompleted: entry?.lastSuccessAt !== undefined,
    lastCompletedAt: entry?.lastSuccessAt,
    lastOutcome: entry?.lastOutcome,
    pending,
    running,
  };
}

/**
 * The progress projection: what fraction of an activity is done.
 *
 * Separate from the status projection above because it answers a different question — status is
 * "is this work live", progress is "how far along". Both are pure over the record table.
 */

/** The subset of a record the progress projection needs. */
export interface ProgressRecord {
  readonly status: ActivityStatus;
  readonly spec: { readonly parent?: ActivityId };
}

/**
 * How much of each parent's declared subtree has finished, keyed by parent id.
 *
 * Built in one pass over the records rather than looked up per parent, so projecting a whole
 * snapshot stays linear instead of rescanning the table once per umbrella.
 */
export function childProgress(records: ReadonlyMap<ActivityId, ProgressRecord>): Map<ActivityId, ActivitySteps> {
  const byParent = new Map<ActivityId, ActivitySteps>();

  for (const record of records.values()) {
    const parent = record.spec.parent;
    if (parent === undefined)
      continue;

    const done = isTerminalStatus(record.status) ? 1 : 0;
    const entry = byParent.get(parent);

    if (entry)
      byParent.set(parent, { current: entry.current + done, total: entry.total + 1 });
    else
      byParent.set(parent, { current: done, total: 1 });
  }

  return byParent;
}

/**
 * How far along one activity is, for the bar.
 *
 * @remarks
 * Any terminal status reads 100, failed and skipped included: no further progress is coming, so
 * excluding them stalls a bar at 3/5 whenever two chains fail. Freshness is the separate axis, and
 * only COMPLETE writes `lastSuccessAt`, so a failed activity stays stale and is retried on its own.
 *
 * `children` wins over `steps`: an activity carrying both is a parent that also reported, and the
 * subtree is the more honest answer.
 *
 * @returns 0-100, or {@link INDETERMINATE} when nothing about the activity can be quantified
 */
function percentageOf(status: ActivityStatus, steps: ActivitySteps | undefined, children?: ActivitySteps): number {
  if (status === Status.COMPLETE || status === Status.SKIPPED || status === Status.FAILED)
    return 100;

  if (children)
    return percentageFromSteps(children.current, children.total);

  return steps ? percentageFromSteps(steps.current, steps.total) : INDETERMINATE;
}

/**
 * The subset of a record {@link projectActivity} reads — structurally satisfied by the
 * orchestrator's `ActivityRecord`, so no adapter is required.
 */
export interface RenderableRecord {
  readonly status: ActivityStatus;
  readonly steps?: ActivitySteps;
  readonly startedAt?: number;
  readonly reason?: string;
  readonly spec: {
    readonly id: ActivityId;
    readonly kind: ActivityKind;
    readonly title: Activity['title'];
    readonly subtitle?: Activity['subtitle'];
    readonly group?: Activity['group'];
    readonly parent?: ActivityId;
    readonly resets?: Activity['resets'];
    readonly priority?: Activity['priority'];
    readonly ephemeral?: boolean;
    readonly rerunnable?: boolean;
    readonly cancel?: () => void;
  };
}

/**
 * A live record as the {@link Activity} every surface renders.
 *
 * `cancellable` is a projection, not a spec field: a PENDING activity can always be dropped from
 * the queue, while a RUNNING one needs a handle to interrupt the work it started.
 */
export function projectActivity(record: RenderableRecord, childSteps?: ActivitySteps): Activity {
  const { spec, status, steps, startedAt, reason } = record;
  return {
    cancellable: status === Status.RUNNING ? Boolean(spec.cancel) : status === Status.PENDING,
    ephemeral: spec.ephemeral,
    group: spec.group,
    id: spec.id,
    kind: spec.kind,
    parent: spec.parent,
    percentage: percentageOf(status, steps, childSteps),
    priority: spec.priority,
    reason,
    rerunnable: Boolean(spec.rerunnable),
    resets: spec.resets,
    source: { type: ActivitySourceType.NATIVE },
    startedAt,
    status,
    steps,
    subtitle: spec.subtitle,
    title: spec.title,
  };
}
