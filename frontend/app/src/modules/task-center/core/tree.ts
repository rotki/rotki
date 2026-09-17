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
 * The leaves of a subtree, `root` itself when it has no children. The nodes {@link subtreeSteps}
 * counts, for a caller that needs to know which ones.
 */
export function subtreeLeaves(children: ReadonlyMap<ActivityId, Activity[]>, root: Activity): Activity[] {
  const leaves: Activity[] = [];
  const seen = new Set<ActivityId>();
  const stack: Activity[] = [root];

  while (stack.length > 0) {
    const activity = stack.pop();
    if (activity === undefined || seen.has(activity.id))
      continue;

    seen.add(activity.id);
    const descendants = children.get(activity.id);

    if (descendants === undefined || descendants.length === 0)
      leaves.push(activity);
    else
      stack.push(...descendants);
  }

  return leaves;
}

/**
 * The nodes a row counts: the deepest descendants of `root`'s own kind when it has any, its leaves otherwise.
 *
 * @remarks
 * A parent is counted in the unit a reader names it by. A chain's sync is "3 of 5 accounts", not
 * "4 of 6" with its decode folded in, because the accounts are the same kind as the chain and the
 * decode is not. A run over several chains' balances counts chains, whatever detection each chain
 * fanned into. A parent with no descendant of its own kind (a history refresh over chains,
 * exchanges and queries) has no such unit and falls back to its leaves.
 *
 * "Deepest" is judged by direct children: a same-kind node counts unless one of its own children is
 * of that kind too.
 */
function subtreeUnits(children: ReadonlyMap<ActivityId, Activity[]>, root: Activity): Activity[] {
  const units: Activity[] = [];
  const seen = new Set<ActivityId>([root.id]);
  const stack: Activity[] = [...(children.get(root.id) ?? [])];

  while (stack.length > 0) {
    const activity = stack.pop();
    if (activity === undefined || seen.has(activity.id))
      continue;

    seen.add(activity.id);
    const descendants = children.get(activity.id) ?? [];
    if (activity.kind === root.kind && !descendants.some(child => child.kind === root.kind))
      units.push(activity);
    stack.push(...descendants);
  }

  return units.length > 0 ? units : subtreeLeaves(children, root);
}

/**
 * How much of a subtree is done, counted in the units {@link subtreeUnits} picks.
 *
 * @remarks
 * Never intermediate rows: an umbrella awaits its chains and a chain awaits its accounts, so
 * counting every row would let each level inflate the total. In a tree of one kind the units are
 * exactly the leaves, the nodes that do the work.
 *
 * Not the same denominator as `Activity.percentage`, which the orchestrator derives from
 * **direct** children only (`projection.ts` `childProgress`). Two-level trees agree; at three
 * levels that is "how many chains finished" and this is "how many accounts finished". A surface
 * must take its number and its bar from the same one.
 *
 * @param children - direct children by parent id, as {@link ActivityTree.children} builds them
 * @param root - the activity whose subtree is counted; counts as its own leaf when childless
 * @returns settled units over total units
 */
export function subtreeSteps(children: ReadonlyMap<ActivityId, Activity[]>, root: Activity): ActivitySteps {
  const units = subtreeUnits(children, root);
  return { current: units.filter(unit => isTerminalStatus(unit.status)).length, total: units.length };
}

/**
 * How far along a subtree is, 0-100, or {@link INDETERMINATE} when nothing in it can be quantified.
 *
 * @remarks
 * Same units as {@link subtreeSteps}, but fractional: a running unit reporting 45% contributes
 * 0.45, not 0. An unquantifiable unit contributes 0 and still counts toward the denominator, so
 * unknown work reads as unfinished rather than leaving the average.
 *
 * This is the number a bar or ring shows, {@link subtreeSteps} the number the text shows. Same
 * denominator, different precision, so "0 of 1 steps" beside a 45% ring is correct. Never pair this
 * with a *different* denominator's text.
 *
 * @param children - direct children by parent id, as {@link ActivityTree.children} builds them
 * @param root - the activity whose subtree is measured
 * @returns 0-100, or {@link INDETERMINATE} (-1) when no unit reports a percentage
 */
export function subtreeProgress(children: ReadonlyMap<ActivityId, Activity[]>, root: Activity): number {
  const units = subtreeUnits(children, root);
  let done = 0;
  let quantifiable = 0;

  for (const unit of units) {
    if (isTerminalStatus(unit.status)) {
      done += 1;
      quantifiable += 1;
    }
    else if (unit.percentage >= 0) {
      done += unit.percentage / 100;
      quantifiable += 1;
    }
  }

  return quantifiable === 0 || units.length === 0 ? INDETERMINATE : Math.round((done / units.length) * 100);
}
