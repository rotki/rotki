import type { TablePaginationData } from '@rotki/ui-library';
import type { RequestFailure } from '@/modules/core/api/request-result';
import type { Collection } from '@/modules/core/common/collection';
import type { FieldDef } from '@/modules/core/table/pill/core/types';
import type { Filters } from '@/modules/history/data-issues/data-issue-filter-keys';
import type { DataIssue, DataIssuesRequestPayload } from '@/modules/history/data-issues/schemas';
import { get } from '@vueuse/shared';
import { omit } from 'es-toolkit';
import { computed, type ComputedRef, type MaybeRefOrGetter, ref, type Ref, type WritableComputedRef } from 'vue';
import { routeWhen, useServerTable } from '@/modules/core/table/use-server-table';
import { DEFAULT_LIST_STATES, IssueState } from '@/modules/history/data-issues/constants';
import { isManualOnlyFilter } from '@/modules/history/data-issues/data-issues-panel-utils';
import { useDataIssueFields } from '@/modules/history/data-issues/use-data-issue-fields';
import { useDataIssues } from '@/modules/history/data-issues/use-data-issues';

interface UseDataIssuesTableReturn {
  readonly activeStates: ComputedRef<string[]>;
  readonly clearFilters: () => void;
  readonly confirmedActive: ComputedRef<boolean>;
  readonly fetchError: Readonly<Ref<RequestFailure | undefined>>;
  readonly fetchIssue: (id: number) => Promise<{ issue?: DataIssue; error?: string }>;
  readonly fields: FieldDef[];
  readonly hasActiveFilters: ComputedRef<boolean>;
  readonly hasRemediatingRows: ComputedRef<boolean>;
  readonly isEmpty: ComputedRef<boolean>;
  readonly isLoading: Ref<boolean>;
  readonly modelFilters: WritableComputedRef<Filters>;
  readonly modelPagination: WritableComputedRef<TablePaginationData>;
  readonly refresh: () => Promise<void>;
  readonly selectConfirmed: () => void;
  readonly selectState: (issueState: IssueState) => void;
  readonly state: Ref<Collection<DataIssue>>;
}

/**
 * Owns the server-paginated table state and filter transitions for the data-issues page, including
 * the default open/unresolved filter and the mutually exclusive Confirmed (`manualOnly`) view.
 */
export function useDataIssuesTable(mainPage: MaybeRefOrGetter<boolean>): UseDataIssuesTableReturn {
  const { fetchData, fetchIssue } = useDataIssues();
  const fields = useDataIssueFields();
  const tableFilters = ref<Filters>({});

  const {
    collection: state,
    error: fetchError,
    filter: modelFilters,
    isLoading,
    pagination: modelPagination,
    refetch: refresh,
    setFilter: updateFilter,
  } = useServerTable<DataIssue, DataIssuesRequestPayload, Filters>({
    fetch: fetchData,
    fields,
    filters: tableFilters,
    params: [{
      isDefault: true,
      to: 'request',
      values: computed<Record<string, unknown>>(() => (isManualOnlyFilter(get(tableFilters).manualOnly) ? {} : { state: [...DEFAULT_LIST_STATES] })),
    }],
    urlState: routeWhen(mainPage),
  });

  const activeStates = computed<string[]>(() => {
    const value = get(modelFilters).state;
    if (Array.isArray(value))
      return value.map(item => item.toString());
    return value ? [value.toString()] : [];
  });

  const confirmedActive = computed<boolean>(() => isManualOnlyFilter(get(modelFilters).manualOnly));
  const hasActiveFilters = computed<boolean>(() => Object.keys(get(modelFilters)).length > 0);
  const isEmpty = computed<boolean>(() => get(state).data.length === 0);
  const hasRemediatingRows = computed<boolean>(() =>
    get(state).data.some(issue => issue.state === IssueState.AUTO_REMEDIATING),
  );

  function selectState(issueState: IssueState): void {
    updateFilter({ ...omit(get(modelFilters), ['manualOnly']), state: [issueState] });
  }

  function selectConfirmed(): void {
    updateFilter({ ...omit(get(modelFilters), ['state']), manualOnly: true });
  }

  function clearFilters(): void {
    updateFilter({});
  }

  return {
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
  };
}
