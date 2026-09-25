import type { Ref } from 'vue';
import { isRequestCancellation } from '@/modules/core/api/request-queue/is-request-cancellation';
import { useDataIssuesApi } from '@/modules/history/data-issues/api/use-data-issues-api';
import { IssueState } from '@/modules/history/data-issues/constants';
import { emptyCounts, type StateCounts, useDataIssuesInboxStore } from '@/modules/history/data-issues/use-data-issues-inbox-store';

/** An issue count, or why there is none. */
type Count = number | 'failed' | 'cancelled';

function isCounted(count: Count): count is number {
  return typeof count === 'number';
}

interface UseDataIssuesSummaryReturn {
  counts: Ref<StateCounts>;
  baselineTotal: Ref<number>;
  /** The last refresh failed, so `counts` are stale and a 0 does not mean all clear. */
  summaryFailed: Ref<boolean>;
  actionableCount: Ref<number>;
  refreshSummary: () => Promise<void>;
  dismissInlinePanels: () => void;
}

/**
 * Loads the inbox summary counts and writes them into the (sync-only) inbox
 * store. Any consumer can read the shared counts from here and trigger a refresh
 * after an action, keeping the badge and the panel in agreement.
 */
export function useDataIssuesSummary(): UseDataIssuesSummaryReturn {
  const { listIssues } = useDataIssuesApi();
  const store = useDataIssuesInboxStore();
  const { actionableCount, baselineTotal, counts, summaryFailed } = storeToRefs(store);

  async function countForStates(states: IssueState[]): Promise<Count> {
    const result = await listIssues({ limit: 1, offset: 0, state: states });
    if (result.ok)
      return result.value.found;

    return isRequestCancellation(result.error.cause) ? 'cancelled' : 'failed';
  }

  /**
   * Counts the issues per summary state and stores them.
   *
   * @remarks
   * The counts are only replaced when every request succeeded. A failed count would read as 0,
   * which the page shows as "all clear", so a failure keeps the previous counts and marks the
   * summary as failed. A cancellation says nothing about the inbox and changes nothing.
   */
  const refreshSummary = async (): Promise<void> => {
    const results = await Promise.all([
      countForStates([IssueState.OPEN]),
      countForStates([IssueState.AUTO_REMEDIATING]),
      countForStates([IssueState.UNRESOLVED]),
      countForStates(Object.values(IssueState)),
    ]);

    const [open, remediating, unresolved, baseline] = results;
    if (!isCounted(open) || !isCounted(remediating) || !isCounted(unresolved) || !isCounted(baseline)) {
      if (results.includes('failed'))
        store.markSummaryFailed();
      return;
    }

    store.setSummary({
      ...emptyCounts(),
      [IssueState.OPEN]: open,
      [IssueState.AUTO_REMEDIATING]: remediating,
      [IssueState.UNRESOLVED]: unresolved,
    }, baseline);
  };

  return {
    actionableCount,
    baselineTotal,
    counts,
    dismissInlinePanels: store.dismissInlinePanels,
    refreshSummary,
    summaryFailed,
  };
}
