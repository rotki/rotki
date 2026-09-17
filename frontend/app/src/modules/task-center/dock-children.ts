import { type Activity, ActivityStatus } from './core/types';

/** One line under an unfolded job: a child as it is, or several failed or skipped leaves that share a reason. */
export type DockChildEntry =
  | { readonly type: 'node'; readonly activity: Activity }
  | { readonly type: 'failed' | 'skipped'; readonly key: string; readonly reason: string | undefined; readonly activities: Activity[] };

/** Reads how a child ended, which for a parent can be a failure beneath it rather than its own status. */
type OutcomeOf = (activity: Activity) => ActivityStatus;

/** The settled statuses whose leaves fold together when they share a reason, as the entry each becomes. */
const GROUPED: Partial<Record<ActivityStatus, 'failed' | 'skipped'>> = {
  [ActivityStatus.FAILED]: 'failed',
  [ActivityStatus.SKIPPED]: 'skipped',
};

/** Settled children read in the order they need attention: failures, then skips, then the rest. */
const SETTLED_ORDER: Partial<Record<ActivityStatus, number>> = {
  [ActivityStatus.FAILED]: 0,
  [ActivityStatus.SKIPPED]: 1,
  [ActivityStatus.CANCELLED]: 2,
  [ActivityStatus.COMPLETE]: 3,
};

/**
 * Orders and groups the children of an unfolded job.
 *
 * @remarks
 * While the job runs, children keep their start order and nothing folds: a row that moves or
 * disappears while it is being read loses the reader's place, which costs more than an order that
 * does not put the busiest first. A finished child stays where it was and only its mark changes.
 *
 * Once the job settles, children sort by {@link SETTLED_ORDER} and failed or skipped leaves with
 * the same status and reason become one entry: a refresh over 21
 * chains otherwise repeats "No tracked accounts on this chain" once per chain, and three accounts
 * missing the same API key repeat that error three times. A reason shared by a single leaf stays a
 * plain row, and a child with children of its own is never folded into a group.
 *
 * @param children - the job's direct children, in start order
 * @param settled - whether the job itself has settled
 * @param isLeaf - whether a child has no children of its own
 * @param outcomeOf - how a settled child ended, so a chain that completed over a failed account sorts as a failure
 */
export function arrangeChildren(
  children: Activity[],
  settled: boolean,
  isLeaf: (activity: Activity) => boolean,
  outcomeOf: OutcomeOf = activity => activity.status,
): DockChildEntry[] {
  if (!settled)
    return children.map(activity => ({ activity, type: 'node' }));

  return groupByReason(sortSettled(children, outcomeOf), isLeaf);
}

/**
 * The failed leaves a folded job surfaces beneath it, with those sharing a reason folded into one entry.
 *
 * @param leaves - failed leaves only, so every one of them is groupable
 */
export function groupFailedLeaves(leaves: Activity[]): DockChildEntry[] {
  return groupByReason(leaves, () => true);
}

function stableSort(activities: Activity[], rank: (activity: Activity) => number): Activity[] {
  return activities
    .map((activity, index) => ({ activity, index }))
    .sort((a, b) => (rank(a.activity) - rank(b.activity)) || a.index - b.index)
    .map(({ activity }) => activity);
}

function sortSettled(children: Activity[], outcomeOf: OutcomeOf): Activity[] {
  return stableSort(children, activity => SETTLED_ORDER[outcomeOf(activity)] ?? Object.keys(SETTLED_ORDER).length);
}

/** Folds failed or skipped leaves sharing a status and reason into one entry, placed where the first of them sorted. */
function groupByReason(ordered: Activity[], isLeaf: (activity: Activity) => boolean): DockChildEntry[] {
  const typeOf = (activity: Activity): 'failed' | 'skipped' | undefined => (isLeaf(activity) ? GROUPED[activity.status] : undefined);
  const keyOf = (activity: Activity): string => `${activity.status}:${activity.reason ?? ''}`;

  const byKey = new Map<string, Activity[]>();
  for (const activity of ordered.filter(activity => typeOf(activity) !== undefined))
    byKey.set(keyOf(activity), [...(byKey.get(keyOf(activity)) ?? []), activity]);

  const placed = new Set<string>();
  const entries: DockChildEntry[] = [];

  for (const activity of ordered) {
    const type = typeOf(activity);
    const group = type === undefined ? [] : byKey.get(keyOf(activity)) ?? [];
    if (type === undefined || group.length < 2) {
      entries.push({ activity, type: 'node' });
    }
    else if (!placed.has(keyOf(activity))) {
      placed.add(keyOf(activity));
      entries.push({ activities: group, key: keyOf(activity), reason: activity.reason, type });
    }
  }

  return entries;
}
