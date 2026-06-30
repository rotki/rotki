import { useAreaVisibilityStore } from '@/modules/core/common/use-area-visibility-store';
import { IssueState } from '@/modules/history/data-issues/constants';
import { PinnedNames } from '@/modules/session/types';

export type StateCounts = Record<IssueState, number>;

export function emptyCounts(): StateCounts {
  return {
    [IssueState.OPEN]: 0,
    [IssueState.AUTO_REMEDIATING]: 0,
    [IssueState.UNRESOLVED]: 0,
    [IssueState.RESOLVED]: 0,
    [IssueState.DISMISSED]: 0,
  };
}

/**
 * Shared summary state for the data issues inbox. Both the top-bar indicator
 * (badge) and the inbox panel read counts from here so the badge and the panel
 * never disagree. The async refresh lives in `useDataIssuesSummary`; this store
 * stays sync-only and just holds state and a setter.
 */
export const useDataIssuesInboxStore = defineStore('history/data-issues-inbox', () => {
  const counts = ref<StateCounts>(emptyCounts());
  const baselineTotal = ref<number>(0);

  /** Whether the floating overlay panel is open. Kept here (not in the history view)
   * so the pinned rail can hand the panel back to the overlay when it is unpinned. */
  const overlayVisible = ref<boolean>(false);

  /** Issues awaiting the user: open + needs-attention. Auto-remediating issues
   * are in progress and need no action, so they are intentionally excluded. */
  const actionableCount = computed<number>(() =>
    get(counts)[IssueState.OPEN] + get(counts)[IssueState.UNRESOLVED]);

  function setSummary(newCounts: StateCounts, baseline: number): void {
    set(counts, newCounts);
    set(baselineTotal, baseline);
  }

  /** Closes the overlay and pinned-rail copies of the inbox. Called when the
   * dedicated data-issues page is shown, so the same list is not displayed twice.
   * Only the data-issues pin is cleared; an unrelated pinned panel is left alone. */
  function dismissInlinePanels(): void {
    set(overlayVisible, false);
    const { pinned } = storeToRefs(useAreaVisibilityStore());
    if (get(pinned)?.name === PinnedNames.DATA_ISSUES)
      set(pinned, null);
  }

  return {
    actionableCount,
    baselineTotal,
    counts,
    dismissInlinePanels,
    overlayVisible,
    setSummary,
  };
});

if (import.meta.hot)
  import.meta.hot.accept(acceptHMRUpdate(useDataIssuesInboxStore, import.meta.hot));
