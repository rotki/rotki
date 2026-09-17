import type { ComputedRef, MaybeRefOrGetter } from 'vue';
import { groupTitle, kindRank } from '@/modules/task-center/core/kinds';
import { isTerminalStatus } from '@/modules/task-center/core/status';
import { someInSubtree } from '@/modules/task-center/core/tree';
import { type Activity, type ActivityId, ActivityKind, ActivityStatus } from '@/modules/task-center/core/types';
import { activityCaches } from '@/modules/task-center/use-dock-activity-detail';

/** One section of a job's work, as "Transaction decoding 4/6". */
export interface JobBreakdownEntry {
  readonly key: string;
  readonly label: string;
  readonly settled: number;
  readonly total: number;
  /**
   * What went wrong in the section, worst first: a failure anywhere beneath it, or work that stopped
   * short (cancelled, or a cache left unfinished). Absent when nothing did.
   */
  readonly problem?: typeof ActivityStatus.FAILED | typeof ActivityStatus.CANCELLED;
}

interface KindCount {
  readonly kind: ActivityKind;
  readonly activities: Activity[];
}

/**
 * A job's descendants counted per kind, each kind at the shallowest depth it appears.
 *
 * @remarks
 * A history refresh holds chains, exchanges and online queries directly, and a decode under each
 * chain, so this reads "chains, exchanges, queries" at depth one and "decodes" at depth two. An
 * account sits under its chain with the chain's own kind, and is left out: the kind was already
 * counted, in the unit a reader names it by. Sections read in kind order, so the line does not
 * reshuffle as work starts.
 */
function countByKind(children: ReadonlyMap<ActivityId, Activity[]>, root: Activity): KindCount[] {
  const claimed = new Map<ActivityKind, number>();
  const counts = new Map<ActivityKind, Activity[]>();
  const seen = new Set<ActivityId>([root.id]);
  let level = children.get(root.id) ?? [];
  let depth = 1;

  while (level.length > 0) {
    const next: Activity[] = [];
    for (const activity of level) {
      if (seen.has(activity.id))
        continue;
      seen.add(activity.id);

      const claimedAt = claimed.get(activity.kind) ?? depth;
      if (claimedAt === depth) {
        claimed.set(activity.kind, depth);
        counts.set(activity.kind, [...(counts.get(activity.kind) ?? []), activity]);
      }
      next.push(...(children.get(activity.id) ?? []));
    }
    level = next;
    depth += 1;
  }

  return Array.from(counts.entries(), ([kind, activities]) => ({ activities, kind }))
    .sort((a, b) => kindRank(a.kind) - kindRank(b.kind));
}

/**
 * What a job is made of, section by section, with the protocol caches its decodes filled, the way
 * the sync panel's header counted chains, locations, decodes and caches.
 *
 * Empty for a job of a single section, since its own "3 of 5" already says the same.
 */
export function useJobBreakdown(
  activity: MaybeRefOrGetter<Activity>,
  children: MaybeRefOrGetter<ReadonlyMap<ActivityId, Activity[]>>,
): ComputedRef<JobBreakdownEntry[]> {
  const { t } = useI18n({ useScope: 'global' });

  return computed<JobBreakdownEntry[]>(() => {
    const root = toValue(activity);
    const tree = toValue(children);
    const byKind = countByKind(tree, root);

    const hasBeneath = (activities: Activity[], status: ActivityStatus): boolean =>
      activities.some(child => someInSubtree(tree, child, node => node.status === status));

    const problemOf = (activities: Activity[]): JobBreakdownEntry['problem'] => {
      if (hasBeneath(activities, ActivityStatus.FAILED))
        return ActivityStatus.FAILED;
      return hasBeneath(activities, ActivityStatus.CANCELLED) ? ActivityStatus.CANCELLED : undefined;
    };

    const entries: JobBreakdownEntry[] = byKind.map(({ activities, kind }) => ({
      key: kind,
      label: groupTitle(kind, activities, t),
      problem: problemOf(activities),
      settled: activities.filter(child => isTerminalStatus(child.status)).length,
      total: activities.length,
    }));

    const filling = byKind.flatMap(({ activities }) => activities)
      .map(child => ({ caches: activityCaches(child), settled: isTerminalStatus(child.status) }));
    const caches = filling.flatMap(({ caches }) => caches);
    if (caches.length > 0) {
      const stopped = filling.some(({ caches, settled }) => settled && caches.some(cache => cache.processed < cache.total));
      entries.push({
        key: ActivityKind.PROTOCOL_CACHE,
        label: t('task_center.group.protocol_cache'),
        problem: stopped ? ActivityStatus.CANCELLED : undefined,
        settled: caches.filter(cache => cache.processed >= cache.total).length,
        total: caches.length,
      });
    }

    return entries.length > 1 ? entries : [];
  });
}
