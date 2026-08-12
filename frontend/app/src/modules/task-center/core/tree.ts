import type { Activity, ActivityId, ActivitySteps } from './types';
import { INDETERMINATE, isTerminalStatus } from './status';

/**
 * The activity tree, read off `Activity.parent`.
 *
 * Producers declare their whole subtree in one tick — a history refresh submits the umbrella, a
 * chain per group and an account per chain before any of it runs — so the shape is known from the
 * first snapshot. Everything downstream of the orchestrator used to flatten it: the render model
 * bucketed by kind, which put a parent and its children in different buckets and (via `kindRank`)
 * guaranteed they were never adjacent.
 *
 * Pure over a snapshot, like the rest of `core/`: no Vue, no orchestrator.
 */
export interface ActivityTree {
  /** Activities with no parent, plus any whose parent is absent from the snapshot. */
  readonly roots: Activity[];
  /** Direct children by parent id. A parent with no children has no entry. */
  readonly children: ReadonlyMap<ActivityId, Activity[]>;
}

/**
 * Running work first, then queued, each oldest first. Inside a subtree the kind is nearly always
 * the same (a chain and its accounts are both TX_SYNC), so `kindRank` — which orders the flat
 * list — carries no information here and start order is what a reader can follow.
 */
function compareSiblings(a: Activity, b: Activity): number {
  const byStart = (a.startedAt ?? Number.MAX_SAFE_INTEGER) - (b.startedAt ?? Number.MAX_SAFE_INTEGER);
  return byStart !== 0 ? byStart : a.id.localeCompare(b.id);
}

/**
 * Groups a flat snapshot into {@link ActivityTree}.
 *
 * An activity whose declared parent is not in the snapshot is treated as a **root**, never
 * dropped: `clearTerminal` prunes settled records, so a parent can legitimately disappear while
 * its children are still live. This mirrors the orchestrator's own stance, where an unknown parent
 * does not gate a child (`orchestrator.ts` `eligible`), so nothing can be wedged — or here,
 * hidden — by a parent that no longer exists.
 */
export function buildTree(activities: Activity[], compareRoots: (a: Activity, b: Activity) => number): ActivityTree {
  const present = new Set(activities.map(activity => activity.id));
  const children = new Map<ActivityId, Activity[]>();
  const roots: Activity[] = [];

  for (const activity of activities) {
    const { parent } = activity;
    if (parent === undefined || !present.has(parent)) {
      roots.push(activity);
      continue;
    }

    const bucket = children.get(parent);
    if (bucket)
      bucket.push(activity);
    else
      children.set(parent, [activity]);
  }

  for (const bucket of children.values())
    bucket.sort(compareSiblings);

  return { children, roots: [...roots].sort(compareRoots) };
}

/** True when `root` or anything beneath it satisfies `predicate`. Same guarded walk as {@link subtreeSteps}. */
export function someInSubtree(
  children: ReadonlyMap<ActivityId, Activity[]>,
  root: Activity,
  predicate: (activity: Activity) => boolean,
): boolean {
  const seen = new Set<ActivityId>();
  const stack: Activity[] = [root];

  while (stack.length > 0) {
    const activity = stack.pop();
    if (activity === undefined || seen.has(activity.id))
      continue;

    if (predicate(activity))
      return true;

    seen.add(activity.id);
    stack.push(...(children.get(activity.id) ?? []));
  }

  return false;
}

/**
 * How much of a subtree is done, counted in **leaves**.
 *
 * Leaves are the only nodes that do work: an umbrella awaits its chains, a chain awaits its
 * accounts, and only the accounts talk to the backend. Counting them is what makes "4 of 11 steps"
 * mean something to a reader — counting rows instead would have every intermediate node inflate
 * the total, and a two-chain refresh would claim more work than it does.
 *
 * ⚠️ Deliberately not the same denominator as `Activity.percentage`, which the orchestrator
 * derives from **direct** children only (`projection.ts` `childProgress`). For a two-level tree
 * they agree; for three levels the percentage is "how many chains finished" while this is "how
 * many accounts finished". Whichever a surface shows, it must show both its number and its bar
 * from the same one.
 */
export function subtreeSteps(children: ReadonlyMap<ActivityId, Activity[]>, root: Activity): ActivitySteps {
  let current = 0;
  let total = 0;

  // Iterative, with a seen-set: a malformed parent chain would otherwise recurse forever, and a
  // task panel is not where a producer's mistake should take the renderer down with it.
  const seen = new Set<ActivityId>();
  const stack: Activity[] = [root];

  while (stack.length > 0) {
    const activity = stack.pop();
    if (activity === undefined || seen.has(activity.id))
      continue;

    seen.add(activity.id);
    const descendants = children.get(activity.id);

    if (descendants === undefined || descendants.length === 0) {
      total += 1;
      if (isTerminalStatus(activity.status))
        current += 1;
      continue;
    }

    stack.push(...descendants);
  }

  return { current, total };
}

/**
 * How far along a subtree is, 0-100, or {@link INDETERMINATE} when nothing in it can be quantified.
 *
 * Same leaves as {@link subtreeSteps}, but a leaf counts fractionally: a running leaf that reports
 * 45% contributes 0.45, not 0. Counting only settled leaves made the header discard the one number
 * a single-task job actually has — a price refresh at 45% rendered its own row at 45% under a
 * header ring pinned at 0%, because "0 of 1 steps" was all the tally could say.
 *
 * A leaf nobody counted contributes 0 while still counting toward the denominator, so unknown work
 * reads as unfinished rather than quietly leaving the average. Only when *no* leaf anywhere is
 * quantifiable does this give up and say so.
 *
 * ⚠️ This is the number a bar or ring shows; {@link subtreeSteps} is the number the text shows.
 * They are the same denominator but not the same precision, so a subtree can legitimately read
 * "0 of 1 steps" beside a 45% ring. Never pair this with a *different* denominator's text.
 */
export function subtreeProgress(children: ReadonlyMap<ActivityId, Activity[]>, root: Activity): number {
  let done = 0;
  let total = 0;
  let quantifiable = 0;

  const seen = new Set<ActivityId>();
  const stack: Activity[] = [root];

  while (stack.length > 0) {
    const activity = stack.pop();
    if (activity === undefined || seen.has(activity.id))
      continue;

    seen.add(activity.id);
    const descendants = children.get(activity.id);

    if (descendants !== undefined && descendants.length > 0) {
      stack.push(...descendants);
      continue;
    }

    total += 1;
    if (isTerminalStatus(activity.status)) {
      done += 1;
      quantifiable += 1;
    }
    else if (activity.percentage >= 0) {
      done += activity.percentage / 100;
      quantifiable += 1;
    }
  }

  return quantifiable === 0 || total === 0 ? INDETERMINATE : Math.round((done / total) * 100);
}
