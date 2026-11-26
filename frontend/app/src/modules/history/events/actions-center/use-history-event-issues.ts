import { logicOr } from '@vueuse/math';
import { get } from '@vueuse/shared';
import { storeToRefs } from 'pinia';
import { computed, type ComputedRef } from 'vue';
import { useI18n } from 'vue-i18n';
import { useTrackedAccountsRow } from '@/modules/accounts/use-tracked-accounts-row';
import { ActionUrgency } from '@/modules/core/action-center/types';
import { useActionCenter, type UseActionCenterReturn } from '@/modules/core/action-center/use-action-center';
import { DuplicateHandlingStatus } from '@/modules/history/events/action-types';
import { DIALOG_TYPES } from '@/modules/history/events/dialog-types';
import { useUndecodedTransactionsCount } from '@/modules/history/events/tx/use-undecoded-transactions-count';
import { useCustomizedEventDuplicates } from '@/modules/history/events/use-customized-event-duplicates';
import { useHistoryEventsStatus } from '@/modules/history/events/use-history-events-status';
import { useInternalTxConflicts } from '@/modules/history/internal-tx-conflicts/use-internal-tx-conflicts';
import { useHistoryStore } from '@/modules/history/use-history-store';
import { createIssue, HISTORY_ISSUE_IDS, type HistoryEventIssue, type HistoryIssueId, type HistoryIssueTarget } from './history-issues';
import { useHistoryDataIssuesRow } from './use-history-data-issues-row';
import { useHistoryMatchingIssues } from './use-history-matching-issues';

export { HISTORY_ISSUE_IDS, type HistoryEventIssue, type HistoryIssueTarget } from './history-issues';

interface UseHistoryEventIssuesReturn extends UseActionCenterReturn<HistoryIssueTarget, HistoryIssueId> {
  /**
   * The history work that moves these counts is running: processing, the balances and
   * auto-matching that follow it, or a matching run the user started.
   */
  busy: ComputedRef<boolean>;
  issues: ComputedRef<HistoryEventIssue[]>;
}

/**
 * Single source for the history "actions center": aggregates every issue type
 * that needs the user's attention into one ordered, uniform list of rows.
 *
 * @remarks
 * The order is not cosmetic. "No tracked accounts" comes first because every other count below it
 * is legitimately zero while it is raised, so a user tracking nothing would otherwise be told there
 * is nothing to do. Locked and ignored-only rows sit last: their counts are real information, but
 * neither asks for anything right now.
 */
export function useHistoryEventIssues(): UseHistoryEventIssuesReturn {
  const { t } = useI18n({ useScope: 'global' });

  const { processing } = useHistoryEventsStatus();
  const { postProcessing } = storeToRefs(useHistoryStore());
  const { autoMatching, bridgesIssue, movementsIssue, sources: matchingSources } = useHistoryMatchingIssues();

  const {
    autoFixCount,
    autoFixGroupIds,
    fetchCustomizedEventDuplicates,
    loading: duplicatesLoading,
    manualReviewCount,
    manualReviewGroupIds,
  } = useCustomizedEventDuplicates();

  const { fetchCounts, issueCount: internalConflictsCount } = useInternalTxConflicts();
  const { items: dataIssuesItems, sources: dataIssuesSources } = useHistoryDataIssuesRow();
  const { decodeMissing, decoding, fetchUndecodedTransactionsBreakdown, undecodedCount } = useUndecodedTransactionsCount();
  const { row: trackedAccounts } = useTrackedAccountsRow();

  const issues = computed<HistoryEventIssue[]>(() => [
    get(trackedAccounts),
    get(movementsIssue),
    get(bridgesIssue),
    createIssue({
      actionLabel: t('transactions.alerts.issues.auto_fix_duplicates.action'),
      count: get(autoFixCount),
      description: t('transactions.alerts.issues.auto_fix_duplicates.description'),
      icon: 'lu-copy',
      id: HISTORY_ISSUE_IDS.AUTO_FIX_DUPLICATES,
      urgency: ActionUrgency.DECISION,
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
      urgency: ActionUrgency.DECISION,
      checkTarget: { kind: 'dialog', options: { type: DIALOG_TYPES.CUSTOMIZED_EVENT_DUPLICATES } },
      target: { groupIds: get(manualReviewGroupIds), kind: 'duplicates', status: DuplicateHandlingStatus.MANUAL_REVIEW },
      title: t('transactions.alerts.issues.manual_review_duplicates.title'),
    }),
    ...get(dataIssuesItems),
    createIssue({
      actionLabel: t('transactions.alerts.issues.internal_conflicts.action'),
      count: get(internalConflictsCount),
      description: t('transactions.alerts.issues.internal_conflicts.description'),
      icon: 'lu-git-merge',
      id: HISTORY_ISSUE_IDS.INTERNAL_CONFLICTS,
      urgency: ActionUrgency.AUTOMATIC,
      target: { kind: 'dialog', options: { type: DIALOG_TYPES.INTERNAL_TX_CONFLICTS } },
      title: t('transactions.alerts.issues.internal_conflicts.title'),
    }),
    createIssue({
      actionLabel: t('transactions.alerts.issues.undecoded.action'),
      count: get(undecodedCount),
      description: t('transactions.alerts.issues.undecoded.description'),
      icon: 'lu-scroll-text',
      id: HISTORY_ISSUE_IDS.UNDECODED,
      loading: get(decoding),
      urgency: ActionUrgency.TODO,
      // decodes in place; the task dock shows the progress by chain
      target: { kind: 'run', run: decodeMissing },
      title: t('transactions.alerts.issues.undecoded.title'),
    }),
  ]);

  const busy = logicOr(processing, postProcessing, autoMatching);

  const center = useActionCenter<HistoryIssueTarget, HistoryIssueId>({
    busy,
    id: 'history-events',
    items: issues,
    sources: [
      ...matchingSources,
      { loading: duplicatesLoading, refresh: fetchCustomizedEventDuplicates },
      { refresh: fetchCounts },
      { refresh: fetchUndecodedTransactionsBreakdown },
      ...dataIssuesSources,
    ],
  });

  return {
    ...center,
    busy,
    issues,
  };
}
