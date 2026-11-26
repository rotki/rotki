import type { ActionCenterOptions } from '@/modules/core/action-center/use-action-center';
import { logicOr } from '@vueuse/math';
import { get } from '@vueuse/shared';
import { computed, type ComputedRef } from 'vue';
import { useI18n } from 'vue-i18n';
import { ActionUrgency } from '@/modules/core/action-center/types';
import { DIALOG_TYPES } from '@/modules/history/events/dialog-types';
import { useUnmatchedAssetMovements } from '@/modules/history/events/use-unmatched-asset-movements';
import { useUnmatchedBridgeTransactions } from '@/modules/history/events/use-unmatched-bridge-transactions';
import { PremiumFeature, useFeatureAccess } from '@/modules/premium/use-feature-access';
import { createIssue, HISTORY_ISSUE_IDS, type HistoryEventIssue, type HistoryIssueId, type HistoryIssueTarget } from './history-issues';

type HistoryIssueSources = ActionCenterOptions<HistoryIssueTarget, HistoryIssueId>['sources'];

interface UseHistoryMatchingIssuesReturn {
  movementsIssue: ComputedRef<HistoryEventIssue>;
  bridgesIssue: ComputedRef<HistoryEventIssue>;
  /** An asset movement or bridge auto-matching run is in flight. */
  autoMatching: ComputedRef<boolean>;
  /** The movements source, then the bridges source. */
  sources: HistoryIssueSources;
}

/**
 * The unmatched asset movements and unmatched bridges rows of the history actions center.
 *
 * @remarks
 * A row whose unmatched count reaches zero switches to showing what was *ignored*, since the dialog
 * behind it is the only place an ignored item can be restored from.
 */
export function useHistoryMatchingIssues(): UseHistoryMatchingIssuesReturn {
  const { t } = useI18n({ useScope: 'global' });
  const { allowed: matchingAllowed, minimumTier: matchingTier } = useFeatureAccess(PremiumFeature.ASSET_MOVEMENT_MATCHING);

  const {
    autoMatchLoading,
    ignoredCount: ignoredMovementsCount,
    loading: movementsLoading,
    refreshUnmatchedAssetMovements,
    unmatchedCount: unmatchedMovementsCount,
  } = useUnmatchedAssetMovements();

  const {
    autoMatchLoading: bridgeAutoMatchLoading,
    ignoredCount: ignoredBridgesCount,
    loading: bridgesLoading,
    refreshUnmatchedBridgeTransactions,
    unmatchedCount: unmatchedBridgesCount,
  } = useUnmatchedBridgeTransactions();

  const movementsIgnoredOnly = computed<boolean>(() => get(unmatchedMovementsCount) === 0 && get(ignoredMovementsCount) > 0);
  const bridgesIgnoredOnly = computed<boolean>(() => get(unmatchedBridgesCount) === 0 && get(ignoredBridgesCount) > 0);

  const movementsIssue = computed<HistoryEventIssue>(() => createIssue({
    actionLabel: get(movementsIgnoredOnly) ? t('transactions.alerts.review_ignored') : t('transactions.alerts.issues.unmatched_movements.action'),
    count: get(movementsIgnoredOnly) ? get(ignoredMovementsCount) : get(unmatchedMovementsCount),
    description: get(movementsIgnoredOnly) ? t('transactions.alerts.ignored_description') : t('transactions.alerts.issues.unmatched_movements.description'),
    icon: 'lu-arrow-left-right',
    id: HISTORY_ISSUE_IDS.UNMATCHED_MOVEMENTS,
    informational: get(movementsIgnoredOnly),
    loading: get(autoMatchLoading),
    locked: !get(matchingAllowed),
    minimumTier: get(matchingTier),
    urgency: get(movementsIgnoredOnly) ? ActionUrgency.AUTOMATIC : ActionUrgency.DECISION,
    target: { kind: 'dialog', options: { type: DIALOG_TYPES.MATCH_ASSET_MOVEMENTS } },
    title: t('transactions.alerts.issues.unmatched_movements.title'),
  }));

  const bridgesIssue = computed<HistoryEventIssue>(() => createIssue({
    actionLabel: get(bridgesIgnoredOnly) ? t('transactions.alerts.review_ignored') : t('transactions.alerts.issues.unmatched_bridges.action'),
    count: get(bridgesIgnoredOnly) ? get(ignoredBridgesCount) : get(unmatchedBridgesCount),
    description: get(bridgesIgnoredOnly) ? t('transactions.alerts.ignored_description') : t('transactions.alerts.issues.unmatched_bridges.description'),
    icon: 'lu-git-compare-arrows',
    id: HISTORY_ISSUE_IDS.UNMATCHED_BRIDGES,
    informational: get(bridgesIgnoredOnly),
    loading: get(bridgeAutoMatchLoading),
    locked: !get(matchingAllowed),
    minimumTier: get(matchingTier),
    urgency: get(bridgesIgnoredOnly) ? ActionUrgency.AUTOMATIC : ActionUrgency.DECISION,
    target: { kind: 'dialog', options: { type: DIALOG_TYPES.MATCH_BRIDGE_TRANSACTIONS } },
    title: t('transactions.alerts.issues.unmatched_bridges.title'),
  }));

  const autoMatching = logicOr(autoMatchLoading, bridgeAutoMatchLoading);

  return {
    autoMatching,
    bridgesIssue,
    movementsIssue,
    sources: [
      {
        loading: movementsLoading,
        refresh: refreshUnmatchedAssetMovements,
        rescan: async (): Promise<void> => refreshUnmatchedAssetMovements(true),
      },
      {
        loading: bridgesLoading,
        refresh: refreshUnmatchedBridgeTransactions,
        rescan: async (): Promise<void> => refreshUnmatchedBridgeTransactions(true),
      },
    ],
  };
}
