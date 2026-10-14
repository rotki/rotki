<script setup lang="ts">
import type { DataTableColumn } from '@rotki/ui-library';
import type { Collection } from '@/modules/core/common/collection';
import type { ProfitLossEvent, ProfitLossEvents, ProfitLossEventsPayload, Report } from '@/modules/reports/report-types';
import { some } from 'es-toolkit/compat';
import { AssetAmountDisplay, FiatDisplay } from '@/modules/assets/amount-display/components';
import AssetDetails from '@/modules/assets/AssetDetails.vue';
import { getCollectionData } from '@/modules/core/common/data/collection-utils';
import TableFrame from '@/modules/core/table/TableFrame.vue';
import { TableId, useRememberTableSorting } from '@/modules/core/table/use-remember-table-sorting';
import { useServerTable } from '@/modules/core/table/use-server-table';
import { useTableEmptyState } from '@/modules/core/table/use-table-empty-state';
import UpgradeRow from '@/modules/history/UpgradeRow.vue';
import CostBasisTable from '@/modules/reports/CostBasisTable.vue';
import ProfitLossEventNotes from '@/modules/reports/ProfitLossEventNotes.vue';
import ProfitLossEventType from '@/modules/reports/ProfitLossEventType.vue';
import { stoppedAtPlanLimit } from '@/modules/reports/report-utils';
import ReportProfitLossEventAction from '@/modules/reports/ReportProfitLossEventAction.vue';
import { useReportOperations } from '@/modules/reports/use-report-operations';
import DateDisplay from '@/modules/shell/components/display/DateDisplay.vue';

interface GroupLine {
  top: boolean;
  bottom: boolean;
}

interface PnLItem extends ProfitLossEvent {
  id: number;
  groupLine: GroupLine;
}

const reportEvents = defineModel<Collection<ProfitLossEvent>>('reportEvents', { required: true });

const {
  refreshing = false,
  report,
} = defineProps<{
  report: Report;
  refreshing?: boolean;
}>();

const { t } = useI18n({ useScope: 'global' });

const expanded = ref<PnLItem[]>([]);

const { fetchReportEvents } = useReportOperations();

const {
  collection: state,
  error,
  isLoading,
  pagination,
  refetch: fetchData,
  sort,
} = useServerTable<
  ProfitLossEvent,
  ProfitLossEventsPayload
>({
  fetch: fetchReportEvents,
  params: [{
    to: 'both',
    values: computed<Record<string, unknown>>(() => ({
      reportId: report.identifier,
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

useRememberTableSorting<PnLItem>(TableId.REPORT_EVENTS, sort, tableHeaders);

const { data, limit } = getCollectionData<ProfitLossEvent>(state);

const showPlanLimit = computed<boolean>(() => stoppedAtPlanLimit(report, get(limit)));

const items = computed<PnLItem[]>(() => {
  const dataVal = get(data);
  return dataVal.map((value, index) => ({
    ...value,
    groupLine: checkGroupLine(dataVal, index),
    id: index,
  }));
});

function checkGroupLine(entries: ProfitLossEvents, index: number): GroupLine {
  const groupId = entries[index]?.groupId;
  if (!groupId)
    return { bottom: false, top: false };

  return {
    bottom: index + 1 < entries.length && groupId === entries[index + 1]?.groupId,
    top: index > 0 && groupId === entries[index - 1]?.groupId,
  };
}

function isExpanded(id: number) {
  return some(get(expanded), { id });
}

function expand(item: PnLItem) {
  set(expanded, isExpanded(item.id) ? [] : [item]);
}

watch(state, (state) => {
  set(reportEvents, state);
});

onMounted(async () => {
  await fetchData();
});
</script>

<template>
  <section class="flex flex-col gap-3">
    <h2 class="text-base font-semibold text-rui-text">
      {{ t('common.events') }}
    </h2>
    <TableFrame>
      <RuiDataTable
        v-model:expanded="expanded"
        v-model:sort.external="sort"
        v-model:pagination.external="pagination"
        :cols="tableHeaders"
        :empty="emptyState"
        :rows="items"
        :loading="isLoading || refreshing"
        row-attr="id"
        single-expand
        sticky-header
        data-testid="report-events-table"
      >
        <template #item.group="{ row }">
          <RuiTooltip
            v-if="row.groupId && (row.groupLine.top || row.groupLine.bottom)"
            :options="{ placement: 'right' }"
            :open-delay="400"
            class="h-full block!"
          >
            <template #activator>
              <div class="relative h-full w-2.5 ml-6">
                <div
                  v-if="row.groupLine.top"
                  class="absolute h-1/2 left-1/2 w-0 transform -translate-x-1/2 border-l-2 border-dashed border-rui-primary top-0"
                />
                <div class="absolute left-1/2 top-1/2 transform -translate-x-1/2 -translate-y-1/2 w-2.5 h-2.5 rounded-full bg-rui-primary" />
                <div
                  v-if="row.groupLine.bottom"
                  class="absolute h-1/2 left-1/2 w-0 transform -translate-x-1/2 border-l-2 border-dashed border-rui-primary bottom-0"
                />
              </div>
            </template>
            <span>{{ t('profit_loss_events.same_action') }}</span>
          </RuiTooltip>
        </template>
        <template #item.timestamp="{ row }">
          <DateDisplay :timestamp="row.timestamp" />
        </template>
        <template #item.type="{ row }">
          <ProfitLossEventType
            :type="row.type"
            :location="row.location"
          />
        </template>
        <template #item.asset="{ row }">
          <AssetDetails
            :asset="row.assetIdentifier"
            :display="{ iconOnly: true, size: '24px' }"
          />
        </template>
        <template #item.free_amount="{ row }">
          <AssetAmountDisplay
            :amount="row.freeAmount"
            :asset="row.assetIdentifier || ''"
          />
        </template>
        <template #item.taxable_amount="{ row }">
          <AssetAmountDisplay
            :amount="row.taxableAmount"
            :asset="row.assetIdentifier || ''"
          />
        </template>
        <template #item.price="{ row }">
          <FiatDisplay
            :value="row.price"
            no-scramble
            :currency="report.settings.profitCurrency ?? undefined"
          />
        </template>
        <template #item.pnl_taxable="{ row }">
          <FiatDisplay
            :value="row.pnlTaxable"
            :currency="report.settings.profitCurrency ?? undefined"
            pnl
          />
        </template>
        <template #item.pnl_free="{ row }">
          <FiatDisplay
            :value="row.pnlFree"
            :currency="report.settings.profitCurrency ?? undefined"
            pnl
          />
        </template>
        <template
          v-if="showPlanLimit"
          #body.prepend="{ colspan }"
        >
          <UpgradeRow
            :limit="report.processedActions"
            :total="report.totalActions"
            :range="{ timeEnd: report.lastProcessedTimestamp, timeStart: report.firstProcessedTimestamp }"
            :colspan="colspan"
            :label="t('plan_limit.labels.events')"
          />
        </template>
        <template #item.notes="{ row }">
          <ProfitLossEventNotes :event="row" />
        </template>
        <template #item.actions="{ row }">
          <ReportProfitLossEventAction
            v-if="report.settings.profitCurrency"
            :event="row"
            :currency="report.settings.profitCurrency"
          />
        </template>
        <template #item.expand="{ row }">
          <RuiTooltip
            :open-delay="400"
            :options="{ placement: 'top' }"
          >
            <template #activator>
              <RuiTableRowExpander
                v-if="row.costBasis"
                :expanded="isExpanded(row.id)"
                @click="expand(row)"
              />
            </template>

            {{ isExpanded(row.id) ? t('profit_loss_events.cost_basis.hide') : t('profit_loss_events.cost_basis.show') }}
          </RuiTooltip>
        </template>
        <template #expanded-item="{ row }">
          <CostBasisTable
            v-if="row.costBasis"
            :show-group-line="row.groupLine.bottom"
            :currency="report.settings.profitCurrency"
            :cost-basis="row.costBasis"
          />
        </template>
      </RuiDataTable>
    </TableFrame>
  </section>
</template>
