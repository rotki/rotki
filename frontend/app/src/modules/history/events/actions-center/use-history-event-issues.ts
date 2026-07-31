import type { RuiIcons } from '@rotki/ui-library';
import type { ComputedRef } from 'vue';
import { useSessionAuthStore } from '@/modules/auth/use-session-auth-store';
import { DuplicateHandlingStatus } from '@/modules/history/events/action-types';
import { DIALOG_TYPES, type DialogShowOptions } from '@/modules/history/events/dialog-types';
import { useUndecodedTransactionsCount } from '@/modules/history/events/tx/use-undecoded-transactions-count';
import { useCustomizedEventDuplicates } from '@/modules/history/events/use-customized-event-duplicates';
import { useHistoryEventsStatus } from '@/modules/history/events/use-history-events-status';
import { useUnmatchedAssetMovements } from '@/modules/history/events/use-unmatched-asset-movements';
import { useUnmatchedBridgeTransactions } from '@/modules/history/events/use-unmatched-bridge-transactions';
import { useInternalTxConflicts } from '@/modules/history/internal-tx-conflicts/use-internal-tx-conflicts';
import { PremiumFeature, useFeatureAccess } from '@/modules/premium/use-feature-access';

export const HISTORY_ISSUE_IDS = {
  AUTO_FIX_DUPLICATES: 'autoFixDuplicates',
  INTERNAL_CONFLICTS: 'internalConflicts',
  MANUAL_REVIEW_DUPLICATES: 'manualReviewDuplicates',
  UNDECODED: 'undecoded',
  UNMATCHED_BRIDGES: 'unmatchedBridges',
  UNMATCHED_MOVEMENTS: 'unmatchedMovements',
} as const;

type HistoryIssueId = typeof HISTORY_ISSUE_IDS[keyof typeof HISTORY_ISSUE_IDS];

/**
 * How much attention a row asks for. `warning` needs a decision from the user,
 * `info` is a to-do that resolves on its own once data is processed and `muted`
 * is handled automatically (rotki retries) and is only worth a look.
 */
export type HistoryIssueSeverity = 'warning' | 'info' | 'muted';

export type HistoryIssueTarget =
  | { kind: 'dialog'; options: DialogShowOptions }
  | { kind: 'duplicates'; status: DuplicateHandlingStatus; groupIds: string[] };

export interface HistoryEventIssue {
  id: HistoryIssueId;
  icon: RuiIcons;
  title: string;
  description: string;
  actionLabel: string;
  count: number;
  severity: HistoryIssueSeverity;
  /** while true the count is not trustworthy yet, so the row is not counted as active */
  loading: boolean;
  /** the count is visible but every action behind it needs premium the user lacks */
  locked: boolean;
  /** tier that would unlock the row, when known */
  minimumTier: string | null;
  /** nothing is unmatched anymore, the count is what the user chose to ignore */
  ignoredOnly: boolean;
  /** where the row's action leads */
  target: HistoryIssueTarget;
  /** where the category is opened from the cleared strip, when it has nothing pending */
  checkTarget: HistoryIssueTarget;
}

interface UseHistoryEventIssuesReturn {
  issues: ComputedRef<HistoryEventIssue[]>;
  activeIssues: ComputedRef<HistoryEventIssue[]>;
  lockedIssues: ComputedRef<HistoryEventIssue[]>;
  reviewIssues: ComputedRef<HistoryEventIssue[]>;
  clearedIssues: ComputedRef<HistoryEventIssue[]>;
  categoryCount: ComputedRef<number>;
  hasIssues: ComputedRef<boolean>;
  /** counts are still incomplete (history syncing, matching or a fetch in flight) */
  checking: ComputedRef<boolean>;
  refreshing: ComputedRef<boolean>;
  refreshAll: () => Promise<void>;
}

/** The parts of a row that are the same for every issue unless stated otherwise. */
type IssueDefinition =
  Omit<HistoryEventIssue, 'loading' | 'locked' | 'minimumTier' | 'ignoredOnly' | 'checkTarget'>
  & Partial<Pick<HistoryEventIssue, 'loading' | 'locked' | 'minimumTier' | 'ignoredOnly' | 'checkTarget'>>;

function createIssue(definition: IssueDefinition): HistoryEventIssue {
  return {
    checkTarget: definition.target,
    ignoredOnly: false,
    loading: false,
    locked: false,
    minimumTier: null,
    ...definition,
  };
}

/**
 * Whether a full scan has completed at least once in this session. Shared, since
 * the trigger and the panel have to agree on whether "no issues" means "nothing
 * to do" or "we have not looked yet".
 */
const scanned = ref<boolean>(false);

/**
 * Single source for the history "actions center": aggregates every issue type
 * that needs the user's attention into one ordered, uniform list of rows.
 */
export function useHistoryEventIssues(): UseHistoryEventIssuesReturn {
  const { t } = useI18n({ useScope: 'global' });

  const { logged } = storeToRefs(useSessionAuthStore());
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
  const { fetchUndecodedTransactionsBreakdown, undecodedCount } = useUndecodedTransactionsCount();

  // With nothing left unmatched the row switches to what was ignored, so those
  // items stay reachable (the dialog is the only place they can be restored from).
  const movementsIgnoredOnly = computed<boolean>(() => get(unmatchedMovementsCount) === 0 && get(ignoredMovementsCount) > 0);
  const bridgesIgnoredOnly = computed<boolean>(() => get(unmatchedBridgesCount) === 0 && get(ignoredBridgesCount) > 0);

  const issues = computed<HistoryEventIssue[]>(() => [
    createIssue({
      actionLabel: get(movementsIgnoredOnly) ? t('transactions.alerts.review_ignored') : t('transactions.alerts.issues.unmatched_movements.action'),
      count: get(movementsIgnoredOnly) ? get(ignoredMovementsCount) : get(unmatchedMovementsCount),
      description: get(movementsIgnoredOnly) ? t('transactions.alerts.ignored_description') : t('transactions.alerts.issues.unmatched_movements.description'),
      icon: 'lu-arrow-left-right',
      id: HISTORY_ISSUE_IDS.UNMATCHED_MOVEMENTS,
      ignoredOnly: get(movementsIgnoredOnly),
      loading: get(autoMatchLoading),
      locked: !get(matchingAllowed),
      minimumTier: get(matchingTier),
      severity: get(movementsIgnoredOnly) ? 'muted' : 'warning',
      target: { kind: 'dialog', options: { type: DIALOG_TYPES.MATCH_ASSET_MOVEMENTS } },
      title: t('transactions.alerts.issues.unmatched_movements.title'),
    }),
    createIssue({
      actionLabel: get(bridgesIgnoredOnly) ? t('transactions.alerts.review_ignored') : t('transactions.alerts.issues.unmatched_bridges.action'),
      count: get(bridgesIgnoredOnly) ? get(ignoredBridgesCount) : get(unmatchedBridgesCount),
      description: get(bridgesIgnoredOnly) ? t('transactions.alerts.ignored_description') : t('transactions.alerts.issues.unmatched_bridges.description'),
      icon: 'lu-git-compare-arrows',
      id: HISTORY_ISSUE_IDS.UNMATCHED_BRIDGES,
      ignoredOnly: get(bridgesIgnoredOnly),
      loading: get(bridgeAutoMatchLoading),
      locked: !get(matchingAllowed),
      minimumTier: get(matchingTier),
      severity: get(bridgesIgnoredOnly) ? 'muted' : 'warning',
      target: { kind: 'dialog', options: { type: DIALOG_TYPES.MATCH_BRIDGE_TRANSACTIONS } },
      title: t('transactions.alerts.issues.unmatched_bridges.title'),
    }),
    createIssue({
      actionLabel: t('transactions.alerts.issues.auto_fix_duplicates.action'),
      count: get(autoFixCount),
      description: t('transactions.alerts.issues.auto_fix_duplicates.description'),
      icon: 'lu-copy',
      id: HISTORY_ISSUE_IDS.AUTO_FIX_DUPLICATES,
      severity: 'warning',
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
      severity: 'warning',
      checkTarget: { kind: 'dialog', options: { type: DIALOG_TYPES.CUSTOMIZED_EVENT_DUPLICATES } },
      target: { groupIds: get(manualReviewGroupIds), kind: 'duplicates', status: DuplicateHandlingStatus.MANUAL_REVIEW },
      title: t('transactions.alerts.issues.manual_review_duplicates.title'),
    }),
    createIssue({
      actionLabel: t('transactions.alerts.issues.internal_conflicts.action'),
      count: get(internalConflictsCount),
      description: t('transactions.alerts.issues.internal_conflicts.description'),
      icon: 'lu-git-merge',
      id: HISTORY_ISSUE_IDS.INTERNAL_CONFLICTS,
      severity: 'muted',
      target: { kind: 'dialog', options: { type: DIALOG_TYPES.INTERNAL_TX_CONFLICTS } },
      title: t('transactions.alerts.issues.internal_conflicts.title'),
    }),
    createIssue({
      actionLabel: t('transactions.alerts.issues.undecoded.action'),
      count: get(undecodedCount),
      description: t('transactions.alerts.issues.undecoded.description'),
      icon: 'lu-scroll-text',
      id: HISTORY_ISSUE_IDS.UNDECODED,
      severity: 'info',
      target: { kind: 'dialog', options: { type: DIALOG_TYPES.DECODING_STATUS } },
      title: t('transactions.alerts.issues.undecoded.title'),
    }),
  ]);

  const raised = computed<HistoryEventIssue[]>(() => get(issues).filter(issue => !issue.loading && issue.count > 0));

  const activeIssues = computed<HistoryEventIssue[]>(() => get(raised).filter(issue => !issue.locked && !issue.ignoredOnly));

  const lockedIssues = computed<HistoryEventIssue[]>(() => get(raised).filter(issue => issue.locked));

  const reviewIssues = computed<HistoryEventIssue[]>(() => get(raised).filter(issue => !issue.locked && issue.ignoredOnly));

  const clearedIssues = computed<HistoryEventIssue[]>(() => get(issues).filter(issue => issue.loading || issue.count === 0));

  const categoryCount = computed<number>(() => get(activeIssues).length);

  const hasIssues = computed<boolean>(() => get(categoryCount) > 0);

  const refreshing = computed<boolean>(() => get(movementsLoading) || get(bridgesLoading) || get(duplicatesLoading));

  // Until the first scan lands the counts are all zero, which is indistinguishable
  // from "nothing to do", so anything reading them has to know they are pending.
  const checking = computed<boolean>(() =>
    !get(scanned) || get(processing) || get(autoMatchLoading) || get(bridgeAutoMatchLoading) || get(refreshing),
  );

  // allSettled, not all: every source reports its own failure, and one rejecting
  // must not pin the whole center to "checking" for the rest of the session.
  const refreshAll = async (): Promise<void> => {
    await Promise.allSettled([
      refreshUnmatchedAssetMovements(),
      refreshUnmatchedBridgeTransactions(),
      fetchCustomizedEventDuplicates(),
      fetchCounts(),
      fetchUndecodedTransactionsBreakdown(),
    ]);
    set(scanned, true);
  };

  // The counts belong to the logged in user, so the next one starts pending again.
  watch(logged, (isLogged) => {
    if (!isLogged)
      set(scanned, false);
  });

  return {
    activeIssues,
    categoryCount,
    checking,
    clearedIssues,
    hasIssues,
    issues,
    lockedIssues,
    reviewIssues,
    refreshAll,
    refreshing,
  };
}
