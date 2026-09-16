import { type Activity, ActivityStatus } from './core/types';

/** One line under an unfolded job: a child as it is, or several skipped leaves that share a reason. */
export type DockChildEntry =
  | { readonly type: 'node'; readonly activity: Activity }
  | { readonly type: 'skipped'; readonly key: string; readonly reason: string | undefined; readonly activities: Activity[] };

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
 * While the job runs, children keep their start order, since rows that move while being read are
 * worse than rows in an unhelpful order. Once it settles they sort by {@link SETTLED_ORDER}, and
 * skipped leaves with the same reason become one entry: a refresh over 21 chains otherwise repeats
 * "No tracked accounts on this chain" once per chain. A reason shared by a single leaf stays a
 * plain row, and a skipped child with children of its own is never folded into a group.
 *
 * @param children - the job's direct children, in start order
 * @param settled - whether the job itself has settled
 * @param isLeaf - whether a child has no children of its own
 */
export function arrangeChildren(
  children: Activity[],
  settled: boolean,
  isLeaf: (activity: Activity) => boolean,
): DockChildEntry[] {
  if (!settled)
    return children.map(activity => ({ activity, type: 'node' }));

  return groupSkips(sortSettled(children), isLeaf);
}

function sortSettled(children: Activity[]): Activity[] {
  const rank = (activity: Activity): number => SETTLED_ORDER[activity.status] ?? Object.keys(SETTLED_ORDER).length;
  return children
    .map((activity, index) => ({ activity, index }))
    .sort((a, b) => (rank(a.activity) - rank(b.activity)) || a.index - b.index)
    .map(({ activity }) => activity);
}

/** Folds skipped leaves sharing a reason into one entry, placed where the first of them sorted. */
function groupSkips(ordered: Activity[], isLeaf: (activity: Activity) => boolean): DockChildEntry[] {
  const groupable = (activity: Activity): boolean => activity.status === ActivityStatus.SKIPPED && isLeaf(activity);
  const reasonOf = (activity: Activity): string => activity.reason ?? '';

  const byReason = new Map<string, Activity[]>();
  for (const activity of ordered.filter(groupable))
    byReason.set(reasonOf(activity), [...(byReason.get(reasonOf(activity)) ?? []), activity]);

  const placed = new Set<string>();
  const entries: DockChildEntry[] = [];

  for (const activity of ordered) {
    const group = groupable(activity) ? byReason.get(reasonOf(activity)) ?? [] : [];
    if (group.length < 2) {
      entries.push({ activity, type: 'node' });
    }
    else if (!placed.has(reasonOf(activity))) {
      placed.add(reasonOf(activity));
      entries.push({ activities: group, key: `skipped:${reasonOf(activity)}`, reason: activity.reason, type: 'skipped' });
    }
  }

  return entries;
}
