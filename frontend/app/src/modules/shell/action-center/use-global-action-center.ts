import type { ComputedRef, MaybeRefOrGetter } from 'vue';
import type { LocationQuery } from 'vue-router';
import { startPromise } from '@shared/utils';
import { type ActionCenterSection, type ActionItem, type ActionTarget, type ActionUrgency, URGENCY_RANK } from '@/modules/core/action-center/types';
import { useActionCenter } from '@/modules/core/action-center/use-action-center';
import { useRefWithDebounce } from '@/modules/core/common/use-ref-debounce';
import { toGlobalTarget } from '@/modules/history/events/actions-center/history-issue-routes';
import { useHistoryEventIssues } from '@/modules/history/events/actions-center/use-history-event-issues';
import { HISTORY_SYNC_ROW_ID } from '@/modules/shell/action-center/row-ids';
import { useAccountingRows } from '@/modules/shell/action-center/use-accounting-rows';
import { useActionCenterProgress } from '@/modules/shell/action-center/use-action-center-progress';
import { useActionCenterSeen } from '@/modules/shell/action-center/use-action-center-seen';
import { SetAside, type SetAsideChange, useActionCenterSnooze } from '@/modules/shell/action-center/use-action-center-snooze';
import { useAssetRows } from '@/modules/shell/action-center/use-asset-rows';
import { useBinancePairsRows } from '@/modules/shell/action-center/use-binance-pairs-rows';
import { useChainRows } from '@/modules/shell/action-center/use-chain-rows';
import { useGnosisPaySafeRows } from '@/modules/shell/action-center/use-gnosis-pay-safe-rows';
import { useHistorySyncRow } from '@/modules/shell/action-center/use-history-sync-row';
import { useIntegrationRows } from '@/modules/shell/action-center/use-integration-rows';
import { usePremiumRows } from '@/modules/shell/action-center/use-premium-rows';

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
 * The re-scan of a source that history work cannot change, so it is read only on the first scan and
 * when the user asks for a re-scan.
 */
async function noRescan(): Promise<void> {}

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

  const history = useHistoryEventIssues();
  const historySyncRow = useHistorySyncRow();
  const integrationRows = useIntegrationRows();
  const premiumRows = usePremiumRows();
  const { refresh: refreshBinancePairsRows, rows: binancePairsRows } = useBinancePairsRows();
  const chainRows = useChainRows();
  const { refresh: refreshAssetRows, rows: assetRows } = useAssetRows();
  const { refresh: refreshAccountingRows, rows: accountingRows } = useAccountingRows();
  const { refresh: refreshGnosisPaySafeRows, rows: gnosisPaySafeRows } = useGnosisPaySafeRows();

  const route = useRoute();
  const historyPageQuery = computed<LocationQuery | undefined>(() => (route.name === '/history/events/' ? route.query : undefined));

  const historyRows = computed<ActionItem[]>(() => {
    const pageQuery = get(historyPageQuery);
    return get(history.issues).map(issue => ({
      ...issue,
      checkTarget: toGlobalTarget(issue.checkTarget, pageQuery),
      choices: issue.choices.map(choice => ({ ...choice, target: toGlobalTarget(choice.target, pageQuery) })),
      options: issue.options.map(option => ({ ...option, target: toGlobalTarget(option.target, pageQuery) })),
      target: toGlobalTarget(issue.target, pageQuery),
    }));
  });

  const { onSnoozeChange, setAsideOf, withSnooze } = useActionCenterSnooze();

  const raisedGroups = computed<ActionCenterSection[]>(() => [
    { id: 'integrations', items: [...get(premiumRows), ...get(integrationRows), ...get(gnosisPaySafeRows), ...get(binancePairsRows)], title: t('action_center.sections.integrations') },
    { id: 'chains', items: get(chainRows), title: t('action_center.sections.chains') },
    { id: 'history', items: [...get(historySyncRow), ...get(historyRows), ...get(accountingRows)], title: t('action_center.sections.history') },
    { id: 'assets', items: get(assetRows), title: t('action_center.sections.assets') },
  ]);

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
    sources: [
      { loading: history.refreshing, refresh: history.refreshAll, rescan: history.rescan },
      { refresh: refreshAssetRows },
      { refresh: refreshBinancePairsRows, rescan: noRescan },
      { refresh: refreshAccountingRows, rescan: noRescan },
      { refresh: refreshGnosisPaySafeRows, rescan: noRescan },
    ],
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
