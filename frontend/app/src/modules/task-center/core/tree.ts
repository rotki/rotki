import type { Activity, ActivityId, ActivitySteps } from './types';
import { INDETERMINATE, isTerminalStatus } from './status';

/**
 * The activity tree, read off `Activity.parent`.
 *
 * Producers declare their whole subtree in one tick — a history refresh submits the umbrella, a
 * chain per group and an account per chain before any of it runs — so the shape is known from the
 * first snapshot.
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
 * @remarks
 * An absent parent is a normal state, not a broken one: `clearTerminal` prunes settled records
 * while their children are still live. The orchestrator takes the same stance in `eligible`, where
 * an unknown parent does not gate a child.
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
 * @remarks
 * Leaves are the only nodes that do work: an umbrella awaits its chains, a chain awaits its
 * accounts, and only the accounts talk to the backend. Counting rows instead would let every
 * intermediate node inflate the total.
 *
 * Not the same denominator as `Activity.percentage`, which the orchestrator derives from
 * **direct** children only (`projection.ts` `childProgress`). Two-level trees agree; at three
 * levels that is "how many chains finished" and this is "how many accounts finished". A surface
 * must take its number and its bar from the same one.
 *
 * @param children - direct children by parent id, as {@link ActivityTree.children} builds them
 * @param root - the activity whose subtree is counted; counts as its own leaf when childless
 * @returns settled leaves over total leaves, both counted across the whole subtree
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
 * @remarks
 * Same leaves as {@link subtreeSteps}, but fractional: a running leaf reporting 45% contributes
 * 0.45, not 0. An unquantifiable leaf contributes 0 and still counts toward the denominator, so
 * unknown work reads as unfinished rather than leaving the average.
 *
 * This is the number a bar or ring shows, {@link subtreeSteps} the number the text shows. Same
 * denominator, different precision, so "0 of 1 steps" beside a 45% ring is correct. Never pair this
 * with a *different* denominator's text.
 *
 * @param children - direct children by parent id, as {@link ActivityTree.children} builds them
 * @param root - the activity whose subtree is measured
 * @returns 0-100, or {@link INDETERMINATE} (-1) when no leaf anywhere reports a percentage
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
