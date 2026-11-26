import type { DataTableColumn, DataTableSortData, TablePaginationData } from '@rotki/ui-library';
import type { Collection } from '@/modules/core/common/collection';
import type { ProfitLossEvent, ProfitLossEvents, ProfitLossEventsPayload, Report } from '@/modules/reports/report-types';
import { get } from '@vueuse/shared';
import { computed, type ComputedRef, type MaybeRefOrGetter, type Ref, toValue, type WritableComputedRef } from 'vue';
import { useI18n } from 'vue-i18n';
import { getCollectionData } from '@/modules/core/common/data/collection-utils';
import { TableId, useRememberTableSorting } from '@/modules/core/table/use-remember-table-sorting';
import { useServerTable } from '@/modules/core/table/use-server-table';
import { type TableEmptyState, useTableEmptyState } from '@/modules/core/table/use-table-empty-state';
import { stoppedAtPlanLimit } from '@/modules/reports/report-utils';
import { useReportOperations } from '@/modules/reports/use-report-operations';

interface GroupLine {
  top: boolean;
  bottom: boolean;
}

export interface PnLItem extends ProfitLossEvent {
  id: number;
  groupLine: GroupLine;
}

interface UseProfitLossEventsTableReturn {
  /** The fetched page of report events. */
  state: Ref<Collection<ProfitLossEvent>>;
  isLoading: Ref<boolean>;
  pagination: WritableComputedRef<TablePaginationData>;
  sort: WritableComputedRef<DataTableSortData<ProfitLossEvent>>;
  emptyState: ComputedRef<TableEmptyState>;
  fetchData: () => Promise<void>;
  tableHeaders: ComputedRef<DataTableColumn<PnLItem>[]>;
  /** The page's events, each marked with the group line it draws to its neighbours. */
  items: ComputedRef<PnLItem[]>;
  /** Whether the report stopped processing at the plan's action limit. */
  showPlanLimit: ComputedRef<boolean>;
}

function checkGroupLine(entries: ProfitLossEvents, index: number): GroupLine {
  const groupId = entries[index]?.groupId;
  if (!groupId)
    return { bottom: false, top: false };

  return {
    bottom: index + 1 < entries.length && groupId === entries[index + 1]?.groupId,
    top: index > 0 && groupId === entries[index - 1]?.groupId,
  };
}

/**
 * The server table of a profit and loss report's events: fetching by report id,
 * remembered sorting, the column set and the group lines between related events.
 */
export function useProfitLossEventsTable(report: MaybeRefOrGetter<Report>): UseProfitLossEventsTableReturn {
  const { t } = useI18n({ useScope: 'global' });

  const { fetchReportEvents } = useReportOperations();

  const {
    collection: state,
    error,
    isLoading,
    pagination: modelPagination,
    refetch: fetchData,
    sort: modelSort,
  } = useServerTable<
    ProfitLossEvent,
    ProfitLossEventsPayload
  >({
    fetch: fetchReportEvents,
    params: [{
      to: 'both',
      values: computed<Record<string, unknown>>(() => ({
        reportId: toValue(report).identifier,
      })),
    }],
    sort: {
      default: [{
        column: 'timestamp',
        direction: 'desc',
      }],
    },
    urlState: { mode: 'route' },
  });

  const emptyState = useTableEmptyState({ error });

  const tableHeaders = computed<DataTableColumn<PnLItem>[]>(() => [
    // widths that hold from page to page (group line room kept, figures start wide), so paging never shifts
    {
      cellClass: 'p-0! h-px',
      class: 'p-0! w-8.5 min-w-8.5',
      key: 'group',
      label: '',
    },
    {
      cellClass: 'px-1!',
      class: 'px-1!',
      key: 'expand',
      label: '',
    },
    // the date over its time, the column only as wide as the date; type and location share one column
    {
      cellClass: 'whitespace-normal',
      class: 'w-28',
      key: 'timestamp',
      label: t('common.datetime'),
      sortable: true,
    },
    {
      align: 'center',
      class: 'w-px whitespace-nowrap',
      key: 'type',
      label: t('profit_loss_events.headers.event'),
    },
    {
      align: 'center',
      class: 'w-px',
      key: 'asset',
      label: t('common.asset'),
      sortable: true,
    },
    {
      align: 'end',
      cellClass: 'whitespace-nowrap',
      class: 'min-w-36',
      key: 'free_amount',
      label: t('profit_loss_events.headers.tax_free_amount'),
    },
    {
      align: 'end',
      cellClass: 'whitespace-nowrap',
      class: 'min-w-36',
      key: 'taxable_amount',
      label: t('profit_loss_events.headers.taxable_amount'),
    },
    {
      align: 'end',
      cellClass: 'whitespace-nowrap',
      class: 'min-w-32',
      key: 'price',
      label: t('common.price'),
    },
    {
      align: 'end',
      cellClass: 'whitespace-nowrap',
      class: 'min-w-36',
      key: 'pnl_free',
      label: t('profit_loss_events.headers.pnl_free'),
      sortable: true,
    },
    {
      align: 'end',
      cellClass: 'whitespace-nowrap',
      class: 'min-w-36',
      key: 'pnl_taxable',
      label: t('profit_loss_events.headers.pnl_taxable'),
      sortable: true,
    },
    {
      cellClass: 'min-w-80',
      key: 'notes',
      label: t('common.notes'),
    },
    {
      align: 'end',
      class: 'w-px',
      key: 'actions',
      label: '',
    },
  ]);

  useRememberTableSorting<PnLItem>(TableId.REPORT_EVENTS, modelSort, tableHeaders);

  const { data, limit } = getCollectionData<ProfitLossEvent>(state);

  const showPlanLimit = computed<boolean>(() => stoppedAtPlanLimit(toValue(report), get(limit)));

  const items = computed<PnLItem[]>(() => {
    const dataVal = get(data);
    return dataVal.map((value, index) => ({
      ...value,
      groupLine: checkGroupLine(dataVal, index),
      id: index,
    }));
  });

  return {
    emptyState,
    fetchData,
    isLoading,
    items,
    pagination: modelPagination,
    showPlanLimit,
    sort: modelSort,
    state,
    tableHeaders,
  };
}
