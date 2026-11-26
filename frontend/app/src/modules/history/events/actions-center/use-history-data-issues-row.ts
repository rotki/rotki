import type { ActionCenterOptions } from '@/modules/core/action-center/use-action-center';
import { startPromise } from '@shared/utils';
import { get } from '@vueuse/shared';
import { storeToRefs } from 'pinia';
import { computed, type ComputedRef, watch } from 'vue';
import { useI18n } from 'vue-i18n';
import { ActionUrgency } from '@/modules/core/action-center/types';
import { isAccountingUpdateEnabled } from '@/modules/core/common/feature-flags';
import { useDataIssueRemediationStore } from '@/modules/history/data-issues/use-data-issue-remediation-store';
import { useDataIssuesSummary } from '@/modules/history/data-issues/use-data-issues-summary';
import { PinnedNames, toPinned } from '@/modules/session/types';
import { createIssue, HISTORY_ISSUE_IDS, type HistoryEventIssue, type HistoryIssueId, type HistoryIssueTarget } from './history-issues';

interface UseHistoryDataIssuesRowReturn {
  /** The data-issues row, or nothing while the accounting update flag is off. */
  items: ComputedRef<HistoryEventIssue[]>;
  /** The data-issues summary source, or nothing while the accounting update flag is off. */
  sources: ActionCenterOptions<HistoryIssueTarget, HistoryIssueId>['sources'];
}

/** The data-issues row of the history actions center, shown only with the accounting update flag. */
export function useHistoryDataIssuesRow(): UseHistoryDataIssuesRowReturn {
  const { t } = useI18n({ useScope: 'global' });
  const dataIssuesEnabled = isAccountingUpdateEnabled();
  const { actionableCount: dataIssuesCount, refreshSummary } = useDataIssuesSummary();

  /**
   * Keeps this badge in step with a remediation run.
   *
   * @remarks
   * The data-issues panel reloads itself on the run's completion; this row is shown outside that
   * panel, so without this it would keep the count it read before the run.
   */
  const { remediationCompleted } = storeToRefs(useDataIssueRemediationStore());
  watch(remediationCompleted, () => startPromise(refreshSummary()));

  const items = computed<HistoryEventIssue[]>(() => (dataIssuesEnabled
    ? [createIssue({
        actionLabel: t('transactions.alerts.issues.data_issues.action'),
        count: get(dataIssuesCount),
        description: t('transactions.alerts.issues.data_issues.description'),
        icon: 'lu-shield-alert',
        id: HISTORY_ISSUE_IDS.DATA_ISSUES,
        urgency: ActionUrgency.DECISION,
        target: { kind: 'pin', panel: toPinned(PinnedNames.DATA_ISSUES, {}) },
        title: t('transactions.alerts.issues.data_issues.title'),
      })]
    : []));

  return {
    items,
    sources: dataIssuesEnabled ? [{ refresh: refreshSummary }] : [],
  };
}
