import type { ComputedRef } from 'vue';
import type { LocationQuery } from 'vue-router';
import { startPromise } from '@shared/utils';
import { type ActionCenterSection, type ActionItem, type ActionTarget, ActionUrgency } from '@/modules/core/action-center/types';
import { useActionCenter } from '@/modules/core/action-center/use-action-center';
import { useRefWithDebounce } from '@/modules/core/common/use-ref-debounce';
import { toGlobalTarget } from '@/modules/history/events/actions-center/history-issue-routes';
import { useHistoryEventIssues } from '@/modules/history/events/actions-center/use-history-event-issues';
import { useHistoryEventsStatus } from '@/modules/history/events/use-history-events-status';
import { useUnmatchedAssetMovements } from '@/modules/history/events/use-unmatched-asset-movements';
import { useUnmatchedBridgeTransactions } from '@/modules/history/events/use-unmatched-bridge-transactions';
import { HISTORY_SYNC_ROW_ID } from '@/modules/shell/action-center/row-ids';
import { useActionCenterSeen } from '@/modules/shell/action-center/use-action-center-seen';
import { useActionCenterSnooze } from '@/modules/shell/action-center/use-action-center-snooze';
import { useAssetRows } from '@/modules/shell/action-center/use-asset-rows';
import { useChainRows } from '@/modules/shell/action-center/use-chain-rows';
import { useHistorySyncRow } from '@/modules/shell/action-center/use-history-sync-row';
import { useIntegrationRows } from '@/modules/shell/action-center/use-integration-rows';

interface UseGlobalActionCenterReturn {
  /** Rows asking for something, grouped by module, with empty modules left out. */
  sections: ComputedRef<ActionCenterSection[]>;
  /** Categories that were checked and came back with nothing pending. */
  cleared: ComputedRef<ActionItem[]>;
  /** How many categories are asking for something. */
  count: ComputedRef<number>;
  /** Ids of the categories that are new, or grew, since the user last closed the center. */
  newIds: ComputedRef<string[]>;
  /** How many categories are new, which is what the badge shows. */
  newCount: ComputedRef<number>;
  /** Records the current counts as seen, called when the center closes. */
  markSeen: () => void;
  checking: ComputedRef<boolean>;
  refreshing: ComputedRef<boolean>;
  refreshAll: () => Promise<void>;
}

const URGENCY_RANK: Record<ActionUrgency, number> = {
  [ActionUrgency.DECISION]: 0,
  [ActionUrgency.TODO]: 1,
  [ActionUrgency.AUTOMATIC]: 2,
};

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
  return !item.loading && item.count > 0;
}

/**
 * The action center for the whole app: every module's rows in one panel, grouped by module.
 *
 * @remarks
 * It owns the scan. The history rows are re-read whenever the history work settles, including
 * immediately on a session that is already synced, and the history events page shows the same rows
 * without scanning them a second time.
 */
export function useGlobalActionCenter(): UseGlobalActionCenterReturn {
  const { t } = useI18n({ useScope: 'global' });

  const history = useHistoryEventIssues();
  const historySyncRow = useHistorySyncRow();
  const integrationRows = useIntegrationRows();
  const chainRows = useChainRows();
  const { refresh: refreshAssetRows, rows: assetRows } = useAssetRows();

  const { processing } = useHistoryEventsStatus();
  const { autoMatchLoading } = useUnmatchedAssetMovements();
  const { autoMatchLoading: bridgeAutoMatchLoading } = useUnmatchedBridgeTransactions();

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

  const { onSnoozeChange, withSnooze } = useActionCenterSnooze();

  const groups = computed<ActionCenterSection[]>(() => [
    { id: 'history', items: [...get(historySyncRow), ...get(historyRows)], title: t('action_center.sections.history') },
    { id: 'chains', items: get(chainRows), title: t('action_center.sections.chains') },
    { id: 'integrations', items: get(integrationRows), title: t('action_center.sections.integrations') },
    { id: 'assets', items: get(assetRows), title: t('action_center.sections.assets') },
  ].map(group => ({ ...group, items: group.items.map(withSnooze) })));

  const center = useActionCenter<ActionTarget, string>({
    busy: history.checking,
    id: 'global',
    items: () => get(groups).flatMap(group => group.items),
    sources: [
      { loading: history.refreshing, refresh: history.refreshAll },
      { refresh: refreshAssetRows },
    ],
  });

  const sections = computed<ActionCenterSection[]>(() => get(groups)
    .map(group => ({ ...group, items: group.items.filter(isRaised).sort((a, b) => rowRank(a) - rowRank(b)) }))
    .filter(section => section.items.length > 0));

  const { forget, markSeen, newIds } = useActionCenterSeen({
    active: center.activeItems,
    checking: center.checking,
    items: () => get(groups).flatMap(group => group.items),
  });

  onSnoozeChange(forget);

  const settled = useRefWithDebounce(logicOr(processing, autoMatchLoading, bridgeAutoMatchLoading), 200);

  watchImmediate(settled, (busy) => {
    if (!busy)
      startPromise(center.refreshAll());
  });

  return {
    checking: center.checking,
    cleared: center.clearedItems,
    count: center.categoryCount,
    markSeen,
    newCount: computed<number>(() => get(newIds).length),
    newIds,
    refreshAll: center.refreshAll,
    refreshing: center.refreshing,
    sections,
  };
}
