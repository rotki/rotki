<script setup lang="ts">
import type { DataTableColumn } from '@rotki/ui-library';
import type { Collection } from '@/modules/core/common/collection';
import type { ProfitLossEvent, ProfitLossEvents, ProfitLossEventsPayload, Report } from '@/modules/reports/report-types';
import { some } from 'es-toolkit/compat';
import { AssetAmountDisplay, FiatDisplay } from '@/modules/assets/amount-display/components';
import AssetDetails from '@/modules/assets/AssetDetails.vue';
import { getCollectionData, setupEntryLimit } from '@/modules/core/common/data/collection-utils';
import { useSupportedChains } from '@/modules/core/common/use-supported-chains';
import { usePaginationFilters } from '@/modules/core/table/use-pagination-filter';
import { TableId, useRememberTableSorting } from '@/modules/core/table/use-remember-table-sorting';
import HistoryEventNote from '@/modules/history/events/HistoryEventNote.vue';
import LocationDisplay from '@/modules/history/LocationDisplay.vue';
import UpgradeRow from '@/modules/history/UpgradeRow.vue';
import CostBasisTable from '@/modules/reports/CostBasisTable.vue';
import ProfitLossEventType from '@/modules/reports/ProfitLossEventType.vue';
import { isTransactionEvent } from '@/modules/reports/report-utils';
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
  fetchData,
  isLoading,
  pagination,
  sort,
  state,
} = usePaginationFilters<
  ProfitLossEvent,
  ProfitLossEventsPayload
>(fetchReportEvents, {
  defaultSortBy: [{
    column: 'timestamp',
    direction: 'desc',
  }],
  extraParams: computed(() => ({
    reportId: report.identifier,
  })),
  history: 'router',
});

const { getChain } = useSupportedChains();

const tableHeaders = computed<DataTableColumn<PnLItem>[]>(() => [
  {
    cellClass: '!p-0 h-px',
    class: '!p-0',
    key: 'group',
    label: '',
  },
  {
    key: 'expand',
    label: '',
  },
  {
    key: 'timestamp',
    label: t('common.datetime'),
    sortable: true,
  },
  {
    align: 'center',
    class: 'w-[6.875rem]',
    key: 'type',
    label: t('common.type'),
  },
  {
    align: 'center',
    cellClass: 'py-2',
    class: 'w-[7.5rem]',
    key: 'location',
    label: t('common.location'),
  },
  {
    key: 'asset',
    label: t('common.asset'),
    sortable: true,
  },
  {
    align: 'end',
    key: 'free_amount',
    label: t('profit_loss_events.headers.tax_free_amount'),
  },
  {
    align: 'end',
    key: 'taxable_amount',
    label: t('profit_loss_events.headers.taxable_amount'),
  },
  {
    align: 'end',
    key: 'price',
    label: t('common.price'),
  },
  {
    align: 'end',
    key: 'pnl_free',
    label: t('profit_loss_events.headers.pnl_free'),
    sortable: true,
  },
  {
    align: 'end',
    key: 'pnl_taxable',
    label: t('profit_loss_events.headers.pnl_taxable'),
    sortable: true,
  },
  {
    key: 'notes',
    label: t('common.notes'),
  },
  {
    align: 'end',
    class: 'w-[8.75rem]',
    key: 'actions',
    label: t('common.actions_text'),
  },
]);

useRememberTableSorting<PnLItem>(TableId.REPORT_EVENTS, sort, tableHeaders);

const { data, entriesFoundTotal, found, limit, total } = getCollectionData<ProfitLossEvent>(state);
const { showUpgradeRow } = setupEntryLimit(limit, found, total, entriesFoundTotal);

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
  <RuiCard>
    <template #header>
      {{ t('common.events') }}
    </template>
    <RuiDataTable
      v-model:expanded="expanded"
      v-model:sort.external="sort"
      v-model:pagination.external="pagination"
      :cols="tableHeaders"
      :rows="items"
      :loading="isLoading || refreshing"
      row-attr="id"
      outlined
      single-expand
      sticky-header
    >
      <template #item.group="{ row }">
        <RuiTooltip
          v-if="row.groupId && (row.groupLine.top || row.groupLine.bottom)"
          :popper="{ placement: 'right' }"
          :open-delay="400"
          class="h-full !block"
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
        <ProfitLossEventType :type="row.type" />
      </template>
      <template #item.location="{ row }">
        <LocationDisplay :identifier="row.location" />
      </template>
      <template #item.asset="{ row }">
        <AssetDetails
          :asset="row.assetIdentifier"
          icon-only
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
        v-if="showUpgradeRow"
        #body.prepend="{ colspan }"
      >
        <UpgradeRow
          events
          :limit="limit"
          :total="total"
          :found="found"
          :time-end="report.lastProcessedTimestamp"
          :time-start="report.firstProcessedTimestamp"
          :colspan="colspan"
          :label="t('common.events')"
        />
      </template>
      <template #item.notes="{ row }">
        <div
          v-if="row.notes"
          class="py-1"
        >
          <HistoryEventNote
            v-if="isTransactionEvent(row)"
            :notes="row.notes"
            :amount="row.taxableAmount.isZero() ? row.freeAmount : row.taxableAmount"
            :asset="row.assetIdentifier"
            :chain="getChain(row.location)"
          />
          <HistoryEventNote
            v-else
            :notes="row.notes"
            :asset="row.assetIdentifier"
          />
        </div>
        <div
          v-else
          class="py-1"
        >
          -
        </div>
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
          :popper="{ placement: 'top' }"
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
  </RuiCard>
</template>
