import { startPromise } from '@shared/utils';
import { watchImmediate } from '@vueuse/core';
import { get, set } from '@vueuse/shared';
import { computed, type ComputedRef, type MaybeRefOrGetter, shallowRef, toValue } from 'vue';
import { useI18n } from 'vue-i18n';
import { type ActionCenterSection, type ActionItem, type ActionTarget, type ActionUrgency, URGENCY_RANK } from '@/modules/core/action-center/types';
import { useActionCenter } from '@/modules/core/action-center/use-action-center';
import { useRefWithDebounce } from '@/modules/core/common/use-ref-debounce';
import { HISTORY_SYNC_ROW_ID } from '@/modules/shell/action-center/row-ids';
import { useActionCenterProgress } from '@/modules/shell/action-center/use-action-center-progress';
import { useActionCenterSeen } from '@/modules/shell/action-center/use-action-center-seen';
import { SetAside, type SetAsideChange, useActionCenterSnooze } from '@/modules/shell/action-center/use-action-center-snooze';
import { useGlobalActionRows } from '@/modules/shell/action-center/use-global-action-rows';

interface UseGlobalActionCenterOptions {
  /** the kinds of put-away rows the user asked to see; the others stay out of the sections */
  revealed?: MaybeRefOrGetter<SetAside[]>;
}

interface UseGlobalActionCenterReturn {
  /**
   * Rows asking for something, grouped by module, with empty modules and unrevealed put-away rows left out.
   * Revealed put-away rows come first, in a group of their own.
   */
  sections: ComputedRef<ActionCenterSection[]>;
  /** How many raised rows the user snoozed or muted, revealed or not. */
  setAsideCounts: ComputedRef<Record<SetAside, number>>;
  /** Categories that were checked and came back with nothing pending. */
  cleared: ComputedRef<ActionItem[]>;
  /** How many categories are asking for something. */
  count: ComputedRef<number>;
  /** The most pressing urgency among them, which sets the trigger's tone; undefined when none are. */
  urgency: ComputedRef<ActionUrgency | undefined>;
  /** Ids of the categories that are new, or grew, since the user last closed the center. */
  newIds: ComputedRef<string[]>;
  /** How many categories are new, which is what the badge shows. */
  newCount: ComputedRef<number>;
  /** The count each lower or cleared category had when the user last closed the center. */
  previousCounts: ComputedRef<Record<string, number>>;
  /**
   * Records the current counts as seen, and as what the next visit's progress compares with, and lets the rows
   * changed during this visit move to their places; called when the center closes.
   */
  markSeen: () => void;
  /** No scan has finished yet this session; later re-scans only show as {@link UseGlobalActionCenterReturn.refreshing}. */
  awaitingFirstScan: ComputedRef<boolean>;
  refreshing: ComputedRef<boolean>;
  refreshAll: () => Promise<void>;
}

/**
 * Where a raised row sits inside its section: the history sync row, which says how current everything
 * under it is, then what needs doing, most urgent first, then what was set aside, then what is locked.
 */
function rowRank(item: ActionItem): number {
  if (item.locked)
    return 5;
  if (item.informational)
    return 4;
  return item.id === HISTORY_SYNC_ROW_ID ? -1 : URGENCY_RANK[item.urgency];
}

function isRaised(item: ActionItem): boolean {
  return item.count > 0;
}

/** Where a raised row is listed: under its module, in the set-aside group at the top, or not at all. */
const Placement = {
  HIDDEN: 'hidden',
  SECTION: 'section',
  SET_ASIDE: 'set-aside',
} as const;

type Placement = (typeof Placement)[keyof typeof Placement];

const SET_ASIDE_SECTION_ID = 'set-aside';

/**
 * The action center for the whole app: every module's rows in one panel, grouped by module.
 *
 * @remarks
 * The sections come in the order their fixes depend on each other: a missing key or indexer leaves the
 * chains and the history behind it incomplete, so keys come first, then chains, then history, then
 * assets. The order is fixed rather than sorted by urgency, so a section never moves while it is read.
 *
 * It owns the scan. The history rows are re-read whenever the history work settles, including
 * immediately on a session that is already synced, and the history events page shows the same rows
 * without scanning them a second time. Settled means after the auto-matching that follows a sync
 * as well, since that moves the unmatched counts again.
 */
export function useGlobalActionCenter(options: UseGlobalActionCenterOptions = {}): UseGlobalActionCenterReturn {
  const { revealed = [] } = options;
  const { t } = useI18n({ useScope: 'global' });

  const { history, raisedGroups, sources } = useGlobalActionRows();

  const { onSnoozeChange, setAsideOf, withSnooze } = useActionCenterSnooze();

  /** How the user put each row away, read off the rows as their sources raised them, by row id. */
  const setAsideIds = computed<Map<string, SetAside>>(() => {
    const ids = new Map<string, SetAside>();
    for (const item of get(raisedGroups).flatMap(group => group.items)) {
      const setAside = setAsideOf(item);
      if (setAside !== undefined)
        ids.set(item.id, setAside);
    }
    return ids;
  });

  const groups = computed<ActionCenterSection[]>(() => get(raisedGroups).map(group => ({ ...group, items: group.items.map(withSnooze) })));

  const center = useActionCenter<ActionTarget, string>({
    busy: history.checking,
    id: 'global',
    items: () => get(groups).flatMap(group => group.items),
    sources,
  });

  /** Rows the user changed by hand while the center is open, by id, with the place they had just before. */
  const settled = shallowRef<ReadonlyMap<string, Placement>>(new Map());

  function isRevealed(setAside: SetAside | undefined): boolean {
    return setAside !== undefined && toValue(revealed).includes(setAside);
  }

  /**
   * Where a row is listed.
   *
   * @remarks
   * A row the user changed while the center is open keeps the place it had, so nothing slides under the pointer
   * after a click; revealing its kind still moves it to the set-aside group, since the user asked for that.
   */
  function placementOf(id: string, setAside: SetAside | undefined): Placement {
    if (isRevealed(setAside))
      return Placement.SET_ASIDE;
    return get(settled).get(id) ?? (setAside === undefined ? Placement.SECTION : Placement.HIDDEN);
  }

  /** A row keeps its rank while it settles, so turning it into a set-aside row does not move it to the end. */
  function sectionRank(item: ActionItem): number {
    return rowRank(get(settled).has(item.id) ? { ...item, informational: false } : item);
  }

  const presentedGroups = computed<ActionCenterSection[]>(() => get(groups)
    .map(group => ({ ...group, items: group.items.map(center.present).filter(isRaised) })));

  function placed(items: ActionItem[], placement: Placement): ActionItem[] {
    return items.filter(item => placementOf(item.id, get(setAsideIds).get(item.id)) === placement);
  }

  const sections = computed<ActionCenterSection[]>(() => [
    {
      id: SET_ASIDE_SECTION_ID,
      items: placed(get(presentedGroups).flatMap(group => group.items), Placement.SET_ASIDE),
      title: t('action_center.sections.set_aside'),
    },
    ...get(presentedGroups).map(group => ({ ...group, items: placed(group.items, Placement.SECTION).sort((a, b) => sectionRank(a) - sectionRank(b)) })),
  ].filter(section => section.items.length > 0));

  const setAsideCounts = computed<Record<SetAside, number>>(() => {
    const counts: Record<SetAside, number> = { [SetAside.MUTED]: 0, [SetAside.SNOOZED]: 0 };
    for (const item of get(presentedGroups).flatMap(group => group.items)) {
      const setAside = get(setAsideIds).get(item.id);
      if (setAside !== undefined)
        counts[setAside] += 1;
    }
    return counts;
  });

  const { forget, markSeen, newIds } = useActionCenterSeen({
    active: center.activeItems,
    checking: center.checking,
    items: () => get(groups).flatMap(group => group.items),
  });

  const { markClosed, previousCounts } = useActionCenterProgress({
    checking: center.awaitingFirstScan,
    items: () => get(groups).flatMap(group => group.items).map(center.present),
  });

  function settle({ from, id }: SetAsideChange): void {
    forget(id);
    set(settled, new Map([...get(settled), [id, placementOf(id, from)]]));
  }

  onSnoozeChange(settle);

  const historySettled = useRefWithDebounce(history.busy, 200);

  watchImmediate(historySettled, (busy) => {
    if (!busy)
      startPromise(center.rescan());
  });

  return {
    awaitingFirstScan: center.awaitingFirstScan,
    cleared: center.clearedItems,
    count: center.categoryCount,
    markSeen: (): void => {
      markSeen();
      markClosed();
      set(settled, new Map());
    },
    newCount: computed<number>(() => get(newIds).length),
    newIds,
    previousCounts,
    refreshAll: center.refreshAll,
    refreshing: center.refreshing,
    sections,
    setAsideCounts,
    urgency: center.urgency,
  };
}
