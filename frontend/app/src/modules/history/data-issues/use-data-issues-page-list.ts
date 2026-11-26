import type { TablePaginationData } from '@rotki/ui-library';
import type { Collection } from '@/modules/core/common/collection';
import type { FieldDef } from '@/modules/core/table/pill/core/types';
import type { Filters } from '@/modules/history/data-issues/data-issue-filter-keys';
import type { DataIssue, DataIssuesRequestPayload } from '@/modules/history/data-issues/schemas';
import type { StateCounts } from '@/modules/history/data-issues/use-data-issues-inbox-store';
import { startPromise } from '@shared/utils';
import { useIntervalFn, useTimeoutFn } from '@vueuse/core';
import { get, set } from '@vueuse/shared';
import { computed, type ComputedRef, type MaybeRefOrGetter, readonly, type Ref, shallowRef, watch, type WritableComputedRef } from 'vue';
import { routeWhen, useServerTable } from '@/modules/core/table/use-server-table';
import { DEFAULT_LIST_STATES, IssueState } from '@/modules/history/data-issues/constants';
import { useDataIssueFields } from '@/modules/history/data-issues/use-data-issue-fields';
import { useDataIssues } from '@/modules/history/data-issues/use-data-issues';
import { useDataIssuesAutoReload } from '@/modules/history/data-issues/use-data-issues-auto-reload';
import { useDataIssuesSummary } from '@/modules/history/data-issues/use-data-issues-summary';

interface UseDataIssuesPageListReturn {
  /** The page of issues the table shows. */
  collection: Ref<Collection<DataIssue>>;
  counts: Ref<StateCounts>;
  /** The last summary refresh failed, so `counts` are stale and a 0 does not mean all clear. */
  summaryFailed: Ref<boolean>;
  dismissInlinePanels: () => void;
  fields: FieldDef[];
  /** The table's pill filters, bound two-way to the filter bar. */
  modelFilters: WritableComputedRef<Filters>;
  /** The table's paging, bound two-way to the table. */
  modelPagination: WritableComputedRef<TablePaginationData>;
  /** Whether the loading indicator shows, held up for a minimum time. */
  showLoading: Readonly<Ref<boolean>>;
  /** All clear only when both the table and the summary read succeeded. */
  isAllClear: ComputedRef<boolean>;
  activeStates: ComputedRef<string[]>;
  hasActiveFilters: ComputedRef<boolean>;
  isEmpty: ComputedRef<boolean>;
  /** Reloads the table and the summary together. */
  reloadAll: () => Promise<void>;
  selectState: (issueState: IssueState) => void;
  clearFilters: () => void;
}

/**
 * The data issues page's server table and the summary above it, kept fresh by a poll while rows
 * auto-remediate and by the completions that change the issues.
 *
 * @param mainPage - whether the list is shown as its own page, which keeps its state in the URL
 */
export function useDataIssuesPageList(mainPage: MaybeRefOrGetter<boolean>): UseDataIssuesPageListReturn {
  const { fetchData } = useDataIssues();
  const { baselineTotal, counts, dismissInlinePanels, refreshSummary, summaryFailed } = useDataIssuesSummary();

  const fields = useDataIssueFields();

  const {
    collection: state,
    error: fetchError,
    filter: filters,
    isLoading,
    pagination,
    refetch: refresh,
    setFilter: updateFilter,
  } = useServerTable<DataIssue, DataIssuesRequestPayload, Filters>({
    fetch: fetchData,
    fields,
    params: [{
      isDefault: true,
      to: 'request',
      values: computed<Record<string, unknown>>(() => ({ state: [...DEFAULT_LIST_STATES] })),
    }],
    urlState: routeWhen(mainPage),
  });

  // The all-clear screen keys off this, not the transient `isLoading`, so a refresh cannot flash the table.
  const loadedOnce = shallowRef<boolean>(false);

  async function reloadAll(): Promise<void> {
    try {
      await Promise.all([refresh(), refreshSummary()]);
    }
    finally {
      set(loadedOnce, true);
    }
  }

  const activeStates = computed<string[]>(() => {
    const value = get(filters).state;
    if (Array.isArray(value))
      return value.map(state => state.toString());
    return value ? [value.toString()] : [];
  });

  const hasAnyIssues = computed<boolean>(() => get(baselineTotal) > 0);

  /** All clear only when both the table and the summary read succeeded: a failed one leaves the table up to say why. */
  const isAllClear = computed<boolean>(() => get(loadedOnce) && !get(hasAnyIssues) && !get(fetchError) && !get(summaryFailed));
  const hasActiveFilters = computed<boolean>(() => Object.keys(get(filters)).length > 0);
  const isEmpty = computed<boolean>(() => get(state).data.length === 0);

  const hasRemediatingRows = computed<boolean>(() =>
    get(state).data.some(issue => issue.state === IssueState.AUTO_REMEDIATING),
  );

  // Holding the indicator this long keeps a fast fetch, or the remediation poll, from flickering it.
  const MIN_LOADING_MS = 500;
  const showLoading = shallowRef<boolean>(false);
  const canHide = shallowRef<boolean>(true);
  const { start: startMinLoading } = useTimeoutFn(() => {
    set(canHide, true);
    if (!get(isLoading))
      set(showLoading, false);
  }, MIN_LOADING_MS, { immediate: false });

  /**
   * Holds the spinner up for at least {@link MIN_LOADING_MS}, so a fast query does not flash it.
   *
   * @remarks
   * A load that finishes inside that window leaves the spinner up and hides nothing: `canHide` is
   * still false, and the timer takes it down when it fires. Only a load still running when the timer
   * fires, or one that finishes after it, is hidden here.
   *
   * @param loading - whether a query is in flight
   */
  function trackLoading(loading: boolean): void {
    if (loading) {
      set(showLoading, true);
      set(canHide, false);
      startMinLoading();
    }
    else if (get(canHide)) {
      set(showLoading, false);
    }
  }

  watch(isLoading, trackLoading);

  function selectState(issueState: IssueState): void {
    updateFilter({ ...get(filters), state: [issueState] });
  }

  function clearFilters(): void {
    updateFilter({});
  }

  const { pause, resume } = useIntervalFn(() => {
    startPromise(reloadAll());
  }, 10_000, { immediate: false });

  watch(hasRemediatingRows, (remediating) => {
    if (remediating)
      resume();
    else
      pause();
  });

  useDataIssuesAutoReload(reloadAll);

  return {
    activeStates,
    clearFilters,
    collection: state,
    counts,
    dismissInlinePanels,
    fields,
    hasActiveFilters,
    isAllClear,
    isEmpty,
    modelFilters: filters,
    modelPagination: pagination,
    reloadAll,
    selectState,
    showLoading: readonly(showLoading),
    summaryFailed,
  };
}
