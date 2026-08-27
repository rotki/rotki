import { groupTitle, kindRank } from './kinds';
import { INDETERMINATE, rollupPercentage, rollupStatus, statusRank } from './status';
import { buildTree } from './tree';
import {
  type Activity,
  type ActivityGroup,
  type ActivityId,
  type ActivityKind,
  type ActivityModel,
  type ActivityPhase,
  ActivityStatus,
  ActivityPhase as Phase,
  type TranslateFn,
} from './types';

/** Stable ordering: by kind priority, then by start time, then by id. */
function compareActivities(a: Activity, b: Activity): number {
  const byKind = kindRank(a.kind) - kindRank(b.kind);
  if (byKind !== 0)
    return byKind;

  const byStart = (a.startedAt ?? 0) - (b.startedAt ?? 0);
  if (byStart !== 0)
    return byStart;

  return a.id.localeCompare(b.id);
}

function toGroup(kind: ActivityKind, activities: Activity[], t: TranslateFn): ActivityGroup {
  const sorted = [...activities].sort(compareActivities);
  return {
    activities: sorted,
    kind,
    percentage: rollupPercentage(sorted.map(a => a.percentage)),
    status: rollupStatus(sorted.map(a => a.status)),
    title: groupTitle(kind, sorted, t),
  };
}

function phaseOf(activities: Activity[]): ActivityPhase {
  if (activities.length === 0)
    return Phase.IDLE;
  if (activities.some(a => a.status === ActivityStatus.RUNNING || a.status === ActivityStatus.PENDING))
    return Phase.WORKING;

  return Phase.DONE;
}

/**
 * Collapses activities that share an id (the same work surfaced by two sources) to a single
 * entry, keeping the most-live status (see {@link statusRank}). Deterministic ids make this
 * exact: e.g. a floor task and its native producer during migration resolve to one activity.
 */
function dedupeById(activities: Activity[]): Activity[] {
  const byId = new Map<ActivityId, Activity>();
  for (const activity of activities) {
    const existing = byId.get(activity.id);
    if (!existing || statusRank(activity.status) < statusRank(existing.status))
      byId.set(activity.id, activity);
  }
  return [...byId.values()];
}

/**
 * Pure assembly of the flat activity list into the render model: dedup by id, groups (ordered
 * by kind priority), the tree, the active/pending splits, the overall rollup + phase, and the
 * single `current` activity the header bar labels. No Vue, no stores — unit-tested with literal
 * inputs.
 */
export function assembleActivityModel(activities: Activity[], t: TranslateFn): ActivityModel {
  const deduped = dedupeById(activities);

  const byKind = new Map<ActivityKind, Activity[]>();
  for (const activity of deduped) {
    const bucket = byKind.get(activity.kind) ?? [];
    bucket.push(activity);
    byKind.set(activity.kind, bucket);
  }

  const groups = Array.from(byKind.entries(), ([kind, group]) => toGroup(kind, group, t))
    .sort((a, b) => kindRank(a.kind) - kindRank(b.kind));

  const ordered = [...deduped].sort(compareActivities);
  const active = ordered.filter(a => a.status === ActivityStatus.RUNNING);
  const pending = ordered.filter(a => a.status === ActivityStatus.PENDING);

  const { children, roots } = buildTree(deduped, compareActivities);

  /**
   * Rolled up from the roots alone.
   *
   * @remarks
   * An umbrella's own percentage is already the mean of its children, so rolling up the per-kind
   * groups instead would count every subtree twice, each time weighted like a single unrelated
   * activity.
   */
  const overallPercentage = rollupPercentage(roots.map(root => root.percentage));
  const current = active[0] ?? pending[0];

  return {
    active,
    children,
    current,
    groups,
    overall: {
      percentage: overallPercentage === INDETERMINATE ? 0 : overallPercentage,
      phase: phaseOf(activities),
    },
    pending,
    roots,
  };
}
