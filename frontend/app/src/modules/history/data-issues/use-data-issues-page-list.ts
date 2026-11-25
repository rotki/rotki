import type { TablePaginationData } from '@rotki/ui-library';
import type { Collection } from '@/modules/core/common/collection';
import type { FieldDef } from '@/modules/core/table/pill/core/types';
import type { IssueState } from '@/modules/history/data-issues/constants';
import type { Filters } from '@/modules/history/data-issues/data-issue-filter-keys';
import type { DataIssue } from '@/modules/history/data-issues/schemas';
import type { StateCounts } from '@/modules/history/data-issues/use-data-issues-inbox-store';
import type { EventPriceUpdatePayload } from '@/modules/history/events/prices/use-event-price-update-trigger';
import type { GroupEventData, StandaloneEventData } from '@/modules/history/management/forms/form-types';
import type { NamedFailure } from '@/modules/shell/components/named-failure';
import { startPromise } from '@shared/utils';
import { useIntervalFn, useTimeoutFn } from '@vueuse/core';
import { get, set } from '@vueuse/shared';
import { computed, type ComputedRef, type MaybeRefOrGetter, readonly, type Ref, shallowRef, watch, type WritableComputedRef } from 'vue';
import { type RemediationRequest, useDataIssueRemediationActions } from '@/modules/history/data-issues/use-data-issue-remediation-actions';
import { useDataIssuesAutoReload } from '@/modules/history/data-issues/use-data-issues-auto-reload';
import { type DetectionResult, useDataIssuesDetection } from '@/modules/history/data-issues/use-data-issues-detection';
import { useDataIssuesSummary } from '@/modules/history/data-issues/use-data-issues-summary';
import { useDataIssuesTable } from '@/modules/history/data-issues/use-data-issues-table';

interface UseDataIssuesPageListReturn {
  /** The page of issues the table shows. */
  collection: Ref<Collection<DataIssue>>;
  confirmedActive: ComputedRef<boolean>;
  confirmedCount: Ref<number>;
  counts: Ref<StateCounts>;
  detect: () => Promise<DetectionResult>;
  detectFailure: Readonly<Ref<NamedFailure | undefined>>;
  detecting: Readonly<Ref<boolean>>;
  /** The last summary refresh failed, so `counts` are stale and a 0 does not mean all clear. */
  summaryFailed: Ref<boolean>;
  dismissInlinePanels: () => void;
  fetchIssue: (id: number) => Promise<{ issue?: DataIssue; error?: string }>;
  fields: FieldDef[];
  /** The table's pill filters, bound two-way to the filter bar. */
  modelEventForm: Ref<GroupEventData | StandaloneEventData | undefined>;
  modelFilters: WritableComputedRef<Filters>;
  modelMatchingOpen: Ref<boolean>;
  /** The table's paging, bound two-way to the table. */
  modelPagination: WritableComputedRef<TablePaginationData>;
  modelPriceUpdate: Ref<EventPriceUpdatePayload | undefined>;
  modelSubModalOpen: Ref<boolean>;
  onModalSaved: () => Promise<void>;
  remediationBusy: Readonly<Ref<boolean>>;
  remediationFailure: Readonly<Ref<NamedFailure | undefined>>;
  remediationModalOpen: ComputedRef<boolean>;
  runRemediation: (request: RemediationRequest) => Promise<void>;
  /** Whether the loading indicator shows, held up for a minimum time. */
  showLoading: Readonly<Ref<boolean>>;
  /** All clear only when both the table and the summary read succeeded. */
  isAllClear: ComputedRef<boolean>;
  activeStates: ComputedRef<string[]>;
  hasActiveFilters: ComputedRef<boolean>;
  isEmpty: ComputedRef<boolean>;
  /** Reloads the table and the summary together. */
  reloadAll: () => Promise<void>;
  selectConfirmed: () => void;
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
  const { baselineTotal, confirmedCount, counts, dismissInlinePanels, refreshSummary, summaryFailed } = useDataIssuesSummary();

  const {
    activeStates,
    clearFilters,
    confirmedActive,
    fetchError,
    fetchIssue,
    fields,
    hasActiveFilters,
    hasRemediatingRows,
    isEmpty,
    isLoading,
    modelFilters,
    modelPagination,
    refresh,
    selectConfirmed,
    selectState,
    state,
  } = useDataIssuesTable(mainPage);

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

  const hasAnyIssues = computed<boolean>(() => get(baselineTotal) > 0);

  /** All clear only when both the table and the summary read succeeded: a failed one leaves the table up to say why. */
  const isAllClear = computed<boolean>(() => get(loadedOnce) && !get(hasAnyIssues) && !get(fetchError) && !get(summaryFailed));

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

  const { detect, detectFailure, detecting } = useDataIssuesDetection(reloadAll);

  const {
    actionFailure: remediationFailure,
    busy: remediationBusy,
    hasModalOpen: remediationModalOpen,
    modelEventForm,
    modelMatchingOpen,
    modelPriceUpdate,
    modelSubModalOpen,
    onModalSaved,
    runRemediation,
  } = useDataIssueRemediationActions(reloadAll);

  return {
    activeStates,
    clearFilters,
    collection: state,
    confirmedActive,
    confirmedCount,
    counts,
    detect,
    detectFailure,
    detecting,
    dismissInlinePanels,
    fetchIssue,
    fields,
    hasActiveFilters,
    isAllClear,
    isEmpty,
    modelEventForm,
    modelFilters,
    modelMatchingOpen,
    modelPagination,
    modelPriceUpdate,
    modelSubModalOpen,
    onModalSaved,
    reloadAll,
    remediationBusy,
    remediationFailure,
    remediationModalOpen,
    runRemediation,
    selectConfirmed,
    selectState,
    showLoading: readonly(showLoading),
    summaryFailed,
  };
}
