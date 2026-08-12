import type { ComputedRef } from 'vue';
import { useTrackedEntities } from '@/modules/accounts/use-tracked-entities';
import { type ActionItem, type ActionItemDefinition, ActionSeverity, type ActionTarget, createActionItem } from '@/modules/core/action-center/types';
import { useActionCenter, type UseActionCenterReturn } from '@/modules/core/action-center/use-action-center';
import { isAccountingUpdateEnabled } from '@/modules/core/common/feature-flags';
import { useDataIssuesSummary } from '@/modules/history/data-issues/use-data-issues-summary';
import { DuplicateHandlingStatus } from '@/modules/history/events/action-types';
import { DIALOG_TYPES, type DialogShowOptions } from '@/modules/history/events/dialog-types';
import { useUndecodedTransactionsCount } from '@/modules/history/events/tx/use-undecoded-transactions-count';
import { useCustomizedEventDuplicates } from '@/modules/history/events/use-customized-event-duplicates';
import { useHistoryEventsStatus } from '@/modules/history/events/use-history-events-status';
import { useUnmatchedAssetMovements } from '@/modules/history/events/use-unmatched-asset-movements';
import { useUnmatchedBridgeTransactions } from '@/modules/history/events/use-unmatched-bridge-transactions';
import { useInternalTxConflicts } from '@/modules/history/internal-tx-conflicts/use-internal-tx-conflicts';
import { PremiumFeature, useFeatureAccess } from '@/modules/premium/use-feature-access';
import { PinnedNames, toPinned } from '@/modules/session/types';

/** Rendered into `data-testid`, so the values are kebab-case like every other test id. */
export const HISTORY_ISSUE_IDS = {
  AUTO_FIX_DUPLICATES: 'auto-fix-duplicates',
  DATA_ISSUES: 'data-issues',
  INTERNAL_CONFLICTS: 'internal-conflicts',
  MANUAL_REVIEW_DUPLICATES: 'manual-review-duplicates',
  NO_TRACKED_ACCOUNTS: 'no-tracked-accounts',
  UNDECODED: 'undecoded',
  UNMATCHED_BRIDGES: 'unmatched-bridges',
  UNMATCHED_MOVEMENTS: 'unmatched-movements',
} as const;

type HistoryIssueId = typeof HISTORY_ISSUE_IDS[keyof typeof HISTORY_ISSUE_IDS];

/** The shared targets, plus the two only the history page can resolve. */
export type HistoryIssueTarget =
  | ActionTarget
  | { kind: 'dialog'; options: DialogShowOptions }
  | { kind: 'duplicates'; status: DuplicateHandlingStatus; groupIds: string[] };

export type HistoryEventIssue = ActionItem<HistoryIssueTarget, HistoryIssueId>;

interface UseHistoryEventIssuesReturn extends UseActionCenterReturn<HistoryIssueTarget, HistoryIssueId> {
  issues: ComputedRef<HistoryEventIssue[]>;
}

function createIssue(definition: ActionItemDefinition<HistoryIssueTarget, HistoryIssueId>): HistoryEventIssue {
  return createActionItem(definition);
}

/**
 * Single source for the history "actions center": aggregates every issue type
 * that needs the user's attention into one ordered, uniform list of rows.
 */
export function useHistoryEventIssues(): UseHistoryEventIssuesReturn {
  const { t } = useI18n({ useScope: 'global' });

  const { processing } = useHistoryEventsStatus();
  // Listing unmatched movements/bridges is free, but every action behind them
  // (find matches, match, ignore, mark external, unlink) is premium-only.
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

  const {
    autoFixCount,
    autoFixGroupIds,
    fetchCustomizedEventDuplicates,
    loading: duplicatesLoading,
    manualReviewCount,
    manualReviewGroupIds,
  } = useCustomizedEventDuplicates();

  const { fetchCounts, issueCount: internalConflictsCount } = useInternalTxConflicts();
  // The inbox is served only in accounting-update builds, so its row (and the four
  // requests behind its count) exist only there.
  const dataIssuesEnabled = isAccountingUpdateEnabled();
  const { actionableCount: dataIssuesCount, refreshSummary } = useDataIssuesSummary();
  const { fetchUndecodedTransactionsBreakdown, undecodedCount } = useUndecodedTransactionsCount();
  const { loading: trackedEntitiesLoading, tracksNothing } = useTrackedEntities();

  // With nothing left unmatched the row switches to what was ignored, so those
  // items stay reachable (the dialog is the only place they can be restored from).
  const movementsIgnoredOnly = computed<boolean>(() => get(unmatchedMovementsCount) === 0 && get(ignoredMovementsCount) > 0);
  const bridgesIgnoredOnly = computed<boolean>(() => get(unmatchedBridgesCount) === 0 && get(ignoredBridgesCount) > 0);

  // Boolean, unlike every other row: there is one thing to do, and the badge counts
  // categories rather than items, so it slots in as a count of one.
  const trackedAccounts = computed<HistoryEventIssue>(() => createIssue({
    actionLabel: t('transactions.alerts.issues.no_tracked_accounts.action'),
    count: get(tracksNothing) ? 1 : 0,
    description: t('transactions.alerts.issues.no_tracked_accounts.description'),
    icon: 'lu-wallet',
    id: HISTORY_ISSUE_IDS.NO_TRACKED_ACCOUNTS,
    loading: get(trackedEntitiesLoading),
    severity: ActionSeverity.WARNING,
    target: { kind: 'route', to: { name: '/balances/blockchain/' } },
    title: t('transactions.alerts.issues.no_tracked_accounts.title'),
  }));

  const issues = computed<HistoryEventIssue[]>(() => [
    // First, because every other count below is legitimately zero when this one is raised:
    // a user tracking nothing would otherwise be told there is nothing to do.
    get(trackedAccounts),
    createIssue({
      actionLabel: get(movementsIgnoredOnly) ? t('transactions.alerts.review_ignored') : t('transactions.alerts.issues.unmatched_movements.action'),
      count: get(movementsIgnoredOnly) ? get(ignoredMovementsCount) : get(unmatchedMovementsCount),
      description: get(movementsIgnoredOnly) ? t('transactions.alerts.ignored_description') : t('transactions.alerts.issues.unmatched_movements.description'),
      icon: 'lu-arrow-left-right',
      id: HISTORY_ISSUE_IDS.UNMATCHED_MOVEMENTS,
      informational: get(movementsIgnoredOnly),
      loading: get(autoMatchLoading),
      locked: !get(matchingAllowed),
      minimumTier: get(matchingTier),
      severity: get(movementsIgnoredOnly) ? ActionSeverity.MUTED : ActionSeverity.WARNING,
      target: { kind: 'dialog', options: { type: DIALOG_TYPES.MATCH_ASSET_MOVEMENTS } },
      title: t('transactions.alerts.issues.unmatched_movements.title'),
    }),
    createIssue({
      actionLabel: get(bridgesIgnoredOnly) ? t('transactions.alerts.review_ignored') : t('transactions.alerts.issues.unmatched_bridges.action'),
      count: get(bridgesIgnoredOnly) ? get(ignoredBridgesCount) : get(unmatchedBridgesCount),
      description: get(bridgesIgnoredOnly) ? t('transactions.alerts.ignored_description') : t('transactions.alerts.issues.unmatched_bridges.description'),
      icon: 'lu-git-compare-arrows',
      id: HISTORY_ISSUE_IDS.UNMATCHED_BRIDGES,
      informational: get(bridgesIgnoredOnly),
      loading: get(bridgeAutoMatchLoading),
      locked: !get(matchingAllowed),
      minimumTier: get(matchingTier),
      severity: get(bridgesIgnoredOnly) ? ActionSeverity.MUTED : ActionSeverity.WARNING,
      target: { kind: 'dialog', options: { type: DIALOG_TYPES.MATCH_BRIDGE_TRANSACTIONS } },
      title: t('transactions.alerts.issues.unmatched_bridges.title'),
    }),
    createIssue({
      actionLabel: t('transactions.alerts.issues.auto_fix_duplicates.action'),
      count: get(autoFixCount),
      description: t('transactions.alerts.issues.auto_fix_duplicates.description'),
      icon: 'lu-copy',
      id: HISTORY_ISSUE_IDS.AUTO_FIX_DUPLICATES,
      severity: ActionSeverity.WARNING,
      checkTarget: { kind: 'dialog', options: { type: DIALOG_TYPES.CUSTOMIZED_EVENT_DUPLICATES } },
      target: { groupIds: get(autoFixGroupIds), kind: 'duplicates', status: DuplicateHandlingStatus.AUTO_FIX },
      title: t('transactions.alerts.issues.auto_fix_duplicates.title'),
    }),
    createIssue({
      actionLabel: t('transactions.alerts.issues.manual_review_duplicates.action'),
      count: get(manualReviewCount),
      description: t('transactions.alerts.issues.manual_review_duplicates.description'),
      icon: 'lu-copy-check',
      id: HISTORY_ISSUE_IDS.MANUAL_REVIEW_DUPLICATES,
      severity: ActionSeverity.WARNING,
      checkTarget: { kind: 'dialog', options: { type: DIALOG_TYPES.CUSTOMIZED_EVENT_DUPLICATES } },
      target: { groupIds: get(manualReviewGroupIds), kind: 'duplicates', status: DuplicateHandlingStatus.MANUAL_REVIEW },
      title: t('transactions.alerts.issues.manual_review_duplicates.title'),
    }),
    ...(dataIssuesEnabled
      ? [createIssue({
          actionLabel: t('transactions.alerts.issues.data_issues.action'),
          count: get(dataIssuesCount),
          description: t('transactions.alerts.issues.data_issues.description'),
          icon: 'lu-shield-alert',
          id: HISTORY_ISSUE_IDS.DATA_ISSUES,
          severity: ActionSeverity.WARNING,
          target: { kind: 'pin', panel: toPinned(PinnedNames.DATA_ISSUES, {}) },
          title: t('transactions.alerts.issues.data_issues.title'),
        })]
      : []),
    createIssue({
      actionLabel: t('transactions.alerts.issues.internal_conflicts.action'),
      count: get(internalConflictsCount),
      description: t('transactions.alerts.issues.internal_conflicts.description'),
      icon: 'lu-git-merge',
      id: HISTORY_ISSUE_IDS.INTERNAL_CONFLICTS,
      severity: ActionSeverity.MUTED,
      target: { kind: 'dialog', options: { type: DIALOG_TYPES.INTERNAL_TX_CONFLICTS } },
      title: t('transactions.alerts.issues.internal_conflicts.title'),
    }),
    createIssue({
      actionLabel: t('transactions.alerts.issues.undecoded.action'),
      count: get(undecodedCount),
      description: t('transactions.alerts.issues.undecoded.description'),
      icon: 'lu-scroll-text',
      id: HISTORY_ISSUE_IDS.UNDECODED,
      severity: ActionSeverity.INFO,
      target: { kind: 'dialog', options: { type: DIALOG_TYPES.DECODING_STATUS } },
      title: t('transactions.alerts.issues.undecoded.title'),
    }),
  ]);

  const center = useActionCenter<HistoryIssueTarget, HistoryIssueId>({
    busy: logicOr(processing, autoMatchLoading, bridgeAutoMatchLoading),
    id: 'history-events',
    items: issues,
    sources: [
      { loading: movementsLoading, refresh: refreshUnmatchedAssetMovements },
      { loading: bridgesLoading, refresh: refreshUnmatchedBridgeTransactions },
      { loading: duplicatesLoading, refresh: fetchCustomizedEventDuplicates },
      { refresh: fetchCounts },
      { refresh: fetchUndecodedTransactionsBreakdown },
      ...(dataIssuesEnabled ? [{ refresh: refreshSummary }] : []),
    ],
  });

  return {
    ...center,
    issues,
  };
}
