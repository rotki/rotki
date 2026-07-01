import type { Ref } from 'vue';
import { useDataIssuesApi } from '@/modules/history/data-issues/api/use-data-issues-api';
import { IssueState } from '@/modules/history/data-issues/constants';
import { emptyCounts, type StateCounts, useDataIssuesInboxStore } from '@/modules/history/data-issues/use-data-issues-inbox-store';

interface UseDataIssuesSummaryReturn {
  counts: Ref<StateCounts>;
  baselineTotal: Ref<number>;
  actionableCount: Ref<number>;
  refreshSummary: () => Promise<void>;
}

/**
 * Loads the inbox summary counts and writes them into the (sync-only) inbox
 * store. Any consumer can read the shared counts from here and trigger a refresh
 * after an action, keeping the badge and the panel in agreement.
 */
export function useDataIssuesSummary(): UseDataIssuesSummaryReturn {
  const { listIssues } = useDataIssuesApi();
  const store = useDataIssuesInboxStore();
  const { actionableCount, baselineTotal, counts } = storeToRefs(store);

  async function countForStates(states: IssueState[]): Promise<number> {
    const result = await listIssues({ limit: 1, offset: 0, state: states });
    return result.ok ? result.value.found : 0;
  }

  const refreshSummary = async (): Promise<void> => {
    const [open, remediating, unresolved, baseline] = await Promise.all([
      countForStates([IssueState.OPEN]),
      countForStates([IssueState.AUTO_REMEDIATING]),
      countForStates([IssueState.UNRESOLVED]),
      countForStates(Object.values(IssueState)),
    ]);

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
    refreshSummary,
  };
}
