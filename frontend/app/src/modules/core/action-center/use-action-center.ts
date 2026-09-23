import type { ComputedRef, MaybeRefOrGetter, Ref } from 'vue';
import type { ActionItem } from '@/modules/core/action-center/types';
import { useSessionAuthStore } from '@/modules/auth/use-session-auth-store';

/** One provider of counts behind a center: how to re-read it, and whether it is reading now. */
interface ActionCenterSource {
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
  /**
   * No scan has finished yet this session, so an empty center means "not looked yet" rather than
   * "nothing to do". Unlike {@link UseActionCenterReturn.checking} it stays false through every later
   * re-scan, which is what lets a center keep its rows on screen while it re-reads them.
   */
  awaitingFirstScan: ComputedRef<boolean>;
  /** a source is reading, or the domain is working: a re-scan is under way */
  refreshing: ComputedRef<boolean>;
  refreshAll: () => Promise<void>;
  /**
   * The item as the center counts it: while it re-reads, with the count its last finished read gave,
   * or none if it has never finished one.
   */
  present: (item: ActionItem<TTarget, TId>) => ActionItem<TTarget, TId>;
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
 * @remarks
 * Domain agnostic on purpose. A center is a list of items plus the sources they were
 * counted from - what the items mean, and where their targets lead, stays with the
 * domain that builds them.
 *
 * A row that is re-reading keeps the count of its last finished read, so the list does not empty and
 * refill around every re-scan; the row itself shows that it is busy. A row that has never finished a
 * read counts as nothing, because its count is not an answer yet.
 */
export function useActionCenter<TTarget extends { kind: string }, TId extends string>(
  options: ActionCenterOptions<TTarget, TId>,
): UseActionCenterReturn<TTarget, TId> {
  const { busy, id, items, sources } = options;

  const { logged } = storeToRefs(useSessionAuthStore());

  const scanned = scannedFlag(id);

  const settledCounts = shallowRef<ReadonlyMap<string, number>>(new Map());

  function recordSettledCounts(current: ActionItem<TTarget, TId>[]): void {
    const known = get(settledCounts);
    const settled = current.filter(item => !item.loading && known.get(item.id) !== item.count);
    if (settled.length === 0)
      return;

    const next = new Map(known);
    for (const item of settled)
      next.set(item.id, item.count);
    set(settledCounts, next);
  }

  function present(item: ActionItem<TTarget, TId>): ActionItem<TTarget, TId> {
    return item.loading ? { ...item, count: get(settledCounts).get(item.id) ?? 0 } : item;
  }

  const presented = computed<ActionItem<TTarget, TId>[]>(() => toValue(items).map(present));

  const raised = computed<ActionItem<TTarget, TId>[]>(() =>
    get(presented).filter(item => item.count > 0),
  );

  const activeItems = computed<ActionItem<TTarget, TId>[]>(() =>
    get(raised).filter(item => !item.locked && !item.informational),
  );

  const lockedItems = computed<ActionItem<TTarget, TId>[]>(() => get(raised).filter(item => item.locked));

  const reviewItems = computed<ActionItem<TTarget, TId>[]>(() =>
    get(raised).filter(item => !item.locked && item.informational),
  );

  const clearedItems = computed<ActionItem<TTarget, TId>[]>(() =>
    get(presented).filter(item => item.count === 0),
  );

  const categoryCount = computed<number>(() => get(activeItems).length);

  const hasItems = computed<boolean>(() => get(categoryCount) > 0);

  const domainBusy = computed<boolean>(() => busy !== undefined && toValue(busy));

  const refreshing = computed<boolean>(() =>
    get(domainBusy) || sources.some(source => source.loading !== undefined && toValue(source.loading)),
  );

  /**
   * Reports whether the counts are still incomplete.
   *
   * @remarks
   * Covers the pre-scan state as well as an in-flight read: before the first scan every count is
   * zero, which reads exactly like "nothing to do", so a consumer must gate on this rather than
   * on the counts alone.
   */
  const checking = computed<boolean>(() => !get(scanned) || get(refreshing));

  const awaitingFirstScan = computed<boolean>(() => !get(scanned));

  /**
   * Re-reads every source, then marks this center scanned whatever the outcome, unless the domain is
   * still busy.
   *
   * @remarks
   * Rejections are absorbed rather than propagated: each source already reports its own failure,
   * and letting one escape would leave `scanned` false and pin the center to `checking` for the
   * rest of the session. A scan that lands while the domain works read counts that are about to
   * change, so it does not count as the first; the next one after the work settles does.
   */
  const refreshAll = async (): Promise<void> => {
    await Promise.allSettled(sources.map(async source => source.refresh()));
    if (!get(domainBusy))
      set(scanned, true);
  };

  watch(() => toValue(items), recordSettledCounts, { flush: 'sync', immediate: true });

  // The counts belong to the logged in user, so the next one starts pending again.
  watch(logged, (isLogged) => {
    if (isLogged)
      return;
    set(scanned, false);
    set(settledCounts, new Map());
  });

  return {
    activeItems,
    awaitingFirstScan,
    categoryCount,
    checking,
    clearedItems,
    hasItems,
    lockedItems,
    present,
    refreshAll,
    refreshing,
    reviewItems,
  };
}
