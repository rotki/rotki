import type { ComputedRef } from 'vue';
import type { Activity, ActivityId } from '@/modules/task-center/core/types';
import { historySyncFlow } from '@/modules/history/events/tx/history-sync.flow';
import { isTerminalStatus } from '@/modules/task-center/core/status';
import { useTaskOrchestrator } from '@/modules/task-center/use-task-orchestrator';

interface UseSyncRollupReturn {
  /** Whether the refresh has work in flight right now. */
  readonly isWorking: ComputedRef<boolean>;
  /** Whether a refresh ran and every part of it has settled. */
  readonly isSettled: ComputedRef<boolean>;
  /** Units of work done, 0-100; `0` when no refresh has been submitted. */
  readonly progress: ComputedRef<number>;
}

/**
 * Is this activity a leaf — the unit the aggregate counts?
 *
 * A parent settles when its children do, so counting both would weight a chain once for itself and
 * once per account, and a chain with ten accounts would move the bar differently from one with two.
 */
function isLeaf(activity: Activity, parents: ReadonlySet<ActivityId>): boolean {
  return !parents.has(activity.id);
}

/**
 * The refresh's own progress, read off the ledger rather than rebuilt from websocket frames.
 *
 * @remarks
 * The unit is **settled leaves over declared leaves**. `history-sync.flow.ts` names every chain,
 * exchange and online query before any of them runs, and each chain in turn declares its accounts
 * and its decode, so the denominator is known at submit time rather than growing as work is
 * discovered. That is what makes the number honest: the three alternatives — a mean of per-activity
 * percentages, completed activities over total, or weighting whole phases against each other — all
 * move the bar when the shape of the work changes rather than when work is done.
 *
 * 🔴🔴 Liveness is `status !== terminal`, never "the model is non-empty". Settled activities stay in
 * the model so the panel can list them, so any predicate shaped like "is anything there" reads true
 * forever after the first completion.
 */
export function useSyncRollup(): UseSyncRollupReturn {
  const { activities } = useTaskOrchestrator();
  const umbrellaId = historySyncFlow.id();

  /** The umbrella and everything beneath it, however deep the producer nested it. */
  const subtree = computed<Activity[]>(() => {
    const all = get(activities);
    const claimed = new Set<ActivityId>([umbrellaId]);
    let growing = true;

    // A single pass would drop any child the snapshot happens to list before its parent.
    while (growing) {
      growing = false;
      for (const activity of all) {
        if (activity.parent !== undefined && claimed.has(activity.parent) && !claimed.has(activity.id)) {
          claimed.add(activity.id);
          growing = true;
        }
      }
    }

    return all.filter(activity => claimed.has(activity.id));
  });

  const leaves = computed<Activity[]>(() => {
    const nodes = get(subtree);
    const parents = new Set<ActivityId>(nodes.map(node => node.parent).filter(id => id !== undefined));
    return nodes.filter(node => isLeaf(node, parents));
  });

  const isWorking = computed<boolean>(() =>
    get(subtree).some(activity => !isTerminalStatus(activity.status)),
  );

  const isSettled = computed<boolean>(() => {
    const nodes = get(subtree);
    return nodes.length > 0 && nodes.every(activity => isTerminalStatus(activity.status));
  });

  const progress = computed<number>(() => {
    const declared = get(leaves);
    if (declared.length === 0)
      return 0;

    const settled = declared.filter(activity => isTerminalStatus(activity.status)).length;
    return Math.round((settled / declared.length) * 100);
  });

  return { isSettled, isWorking, progress };
}
