import type { ComputedRef, MaybeRefOrGetter, Ref } from 'vue';
import type { ActionItem } from '@/modules/core/action-center/types';
import { useSessionAuthStore } from '@/modules/auth/use-session-auth-store';

/** One provider of counts behind a center: how to re-read it, and whether it is reading now. */
export interface ActionCenterSource {
  /** the return value is discarded: a center only cares that the read finished */
  refresh: () => Promise<unknown>;
  /** in-flight state of this source's own read, when it exposes one */
  loading?: MaybeRefOrGetter<boolean>;
}

export interface ActionCenterOptions<TTarget extends { kind: string }, TId extends string> {
  /**
   * Identifies this center. Every consumer passing the same id shares one "has a scan
   * happened yet" flag, which the trigger and the panel have to agree on.
   */
  id: string;
  items: MaybeRefOrGetter<ActionItem<TTarget, TId>[]>;
  sources: ActionCenterSource[];
  /** domain work that makes the counts untrustworthy while it runs */
  busy?: MaybeRefOrGetter<boolean>;
}

export interface UseActionCenterReturn<TTarget extends { kind: string }, TId extends string> {
  /** raised, actionable and not gated: what the badge counts */
  activeItems: ComputedRef<ActionItem<TTarget, TId>[]>;
  /** raised, but every action behind them needs premium the user lacks */
  lockedItems: ComputedRef<ActionItem<TTarget, TId>[]>;
  /** raised, but nothing is pending: the count is what the user set aside */
  reviewItems: ComputedRef<ActionItem<TTarget, TId>[]>;
  /** nothing to do, or not counted yet */
  clearedItems: ComputedRef<ActionItem<TTarget, TId>[]>;
  categoryCount: ComputedRef<number>;
  hasItems: ComputedRef<boolean>;
  /** counts are still incomplete (a source is reading, or the domain is still working) */
  checking: ComputedRef<boolean>;
  refreshing: ComputedRef<boolean>;
  refreshAll: () => Promise<void>;
}

/**
 * Whether a full scan has completed at least once in this session, per center.
 *
 * Module scoped rather than per call, because the trigger and the panel are separate
 * components reading the same center, and they have to agree on whether "nothing to
 * do" means "we have not looked yet". Cleared on logout by every live consumer.
 */
const scannedFlags = new Map<string, Ref<boolean>>();

function scannedFlag(id: string): Ref<boolean> {
  const existing = scannedFlags.get(id);
  if (existing)
    return existing;

  const flag = ref<boolean>(false);
  scannedFlags.set(id, flag);
  return flag;
}

/**
 * The state around a list of {@link ActionItem}s: which of them are asking for something
 * right now, whether the counts can be trusted yet, and how to re-read them.
 *
 * Domain agnostic on purpose. A center is a list of items plus the sources they were
 * counted from - what the items mean, and where their targets lead, stays with the
 * domain that builds them.
 */
export function useActionCenter<TTarget extends { kind: string }, TId extends string>(
  options: ActionCenterOptions<TTarget, TId>,
): UseActionCenterReturn<TTarget, TId> {
  const { busy, id, items, sources } = options;

  const { logged } = storeToRefs(useSessionAuthStore());

  const scanned = scannedFlag(id);

  const raised = computed<ActionItem<TTarget, TId>[]>(() =>
    toValue(items).filter(item => !item.loading && item.count > 0),
  );

  const activeItems = computed<ActionItem<TTarget, TId>[]>(() =>
    get(raised).filter(item => !item.locked && !item.informational),
  );

  const lockedItems = computed<ActionItem<TTarget, TId>[]>(() => get(raised).filter(item => item.locked));

  const reviewItems = computed<ActionItem<TTarget, TId>[]>(() =>
    get(raised).filter(item => !item.locked && item.informational),
  );

  const clearedItems = computed<ActionItem<TTarget, TId>[]>(() =>
    toValue(items).filter(item => item.loading || item.count === 0),
  );

  const categoryCount = computed<number>(() => get(activeItems).length);

  const hasItems = computed<boolean>(() => get(categoryCount) > 0);

  const refreshing = computed<boolean>(() =>
    sources.some(source => source.loading !== undefined && toValue(source.loading)),
  );

  // Until the first scan lands the counts are all zero, which is indistinguishable
  // from "nothing to do", so anything reading them has to know they are pending.
  const checking = computed<boolean>(() =>
    !get(scanned) || (busy !== undefined && toValue(busy)) || get(refreshing),
  );

  // allSettled, not all: every source reports its own failure, and one rejecting
  // must not pin the whole center to "checking" for the rest of the session.
  const refreshAll = async (): Promise<void> => {
    await Promise.allSettled(sources.map(async source => source.refresh()));
    set(scanned, true);
  };

  // The counts belong to the logged in user, so the next one starts pending again.
  watch(logged, (isLogged) => {
    if (!isLogged)
      set(scanned, false);
  });

  return {
    activeItems,
    categoryCount,
    checking,
    clearedItems,
    hasItems,
    lockedItems,
    refreshAll,
    refreshing,
    reviewItems,
  };
}
