<script setup lang="ts">
import type { ProfitLossEvent, ProfitLossEvents, SelectedReport } from '@/types/reports';
import type { DataTableColumn, DataTableOptions, DataTableSortData } from '@rotki/ui-library';
import AssetLink from '@/components/assets/AssetLink.vue';
import AmountDisplay from '@/components/display/amount/AmountDisplay.vue';
import DateDisplay from '@/components/display/DateDisplay.vue';
import AssetIcon from '@/components/helper/display/icons/AssetIcon.vue';
import HistoryEventNote from '@/components/history/events/HistoryEventNote.vue';
import LocationDisplay from '@/components/history/LocationDisplay.vue';
import UpgradeRow from '@/components/history/UpgradeRow.vue';
import CostBasisTable from '@/components/profitloss/CostBasisTable.vue';
import ProfitLossEventType from '@/components/profitloss/ProfitLossEventType.vue';
import ReportProfitLossEventAction from '@/components/profitloss/ReportProfitLossEventAction.vue';
import { useSupportedChains } from '@/composables/info/chains';
import { usePremium } from '@/composables/premium';
import { isTransactionEvent } from '@/utils/report';
import { some } from 'es-toolkit/compat';

interface GroupLine {
  top: boolean;
  bottom: boolean;
}

const props = withDefaults(
  defineProps<{
    report: SelectedReport;
    loading?: boolean;
    refreshing?: boolean;
  }>(),
  {
    loading: false,
    refreshing: false,
  },
);

const emit = defineEmits<{
  (e: 'update:page', page: { reportId: number; offset: number; limit: number }): void;
}>();

const { t } = useI18n();

type PnLItem = ProfitLossEvent & { id: number; groupLine: GroupLine };

const { report } = toRefs(props);

const tablePagination = ref<DataTableOptions<PnLItem>['pagination']>();
const expanded = ref<PnLItem[]>([]);

const sort = ref<DataTableSortData<PnLItem>>({
  column: 'timestamp',
  direction: 'asc',
});

const route = useRoute('/reports/[id]');
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
  },
  {
    align: 'end',
    key: 'pnl_taxable',
    label: t('profit_loss_events.headers.pnl_taxable'),
  },
  {
    key: 'timestamp',
    label: t('common.datetime'),
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

const items = computed<PnLItem[]>(() =>
  get(report).entries.map((value, index) => ({
    ...value,
    groupLine: checkGroupLine(get(report).entries, index),
    id: index,
  })),
);

const itemLength = computed(() => {
  const { entriesFound, entriesLimit } = report.value;
  if (entriesLimit > 0 && entriesLimit <= entriesFound)
    return entriesLimit;

  return entriesFound;
});

const premium = usePremium();

const showUpgradeMessage = computed(() => !premium.value && report.value.totalActions > report.value.processedActions);

function updatePagination(tableOptions: DataTableOptions<PnLItem>) {
  const { pagination } = tableOptions;
  set(tablePagination, pagination);

  if (!pagination)
    return;

  const { limit, page } = pagination;

  const reportId = Number.parseInt(get(route).params.id as string);

  emit('update:page', {
    limit,
    offset: limit * (page - 1),
    reportId,
  });
}

function checkGroupLine(entries: ProfitLossEvents, index: number) {
  const current = entries[index];
  const prev = index - 1 >= 0 ? entries[index - 1] : null;
  const next = index + 1 < entries.length ? entries[index + 1] : null;

  return {
    bottom: !!(current?.groupId && next && current?.groupId === next?.groupId),
    top: !!(current?.groupId && prev && current?.groupId === prev?.groupId),
  };
}

function isExpanded(id: number) {
  return some(get(expanded), { id });
}

function expand(item: PnLItem) {
  set(expanded, isExpanded(item.id) ? [] : [item]);
}
</script>

<template>
  <RuiCard>
    <template #header>
      {{ t('common.events') }}
    </template>
    <RuiDataTable
      v-model:expanded="expanded"
      v-model:sort="sort"
      :cols="tableHeaders"
      :rows="items"
      :loading="loading || refreshing"
      :pagination="{
        limit: tablePagination?.limit ?? 10,
        page: tablePagination?.page ?? 1,
        total: itemLength,
      }"
      :pagination-modifiers="{ external: true }"
      outlined
      single-expand
      sticky-header
      row-attr="id"
      @update:options="updatePagination($event)"
    >
      <template #item.group="{ row }">
        <RuiTooltip
          v-if="row.groupId && (row.groupLine.top || row.groupLine.bottom)"
          :popper="{ placement: 'right' }"
          :open-delay="400"
          class="h-full !block"
        >
          <template #activator>
            <div :class="$style.group">
              <div
                v-if="row.groupLine.top"
                :class="[$style.group__line, $style['group__line-top']]"
              />
              <div :class="$style.group__dot" />
              <div
                v-if="row.groupLine.bottom"
                :class="[$style.group__line, $style['group__line-bottom']]"
              />
            </div>
          </template>
          <span>{{ t('profit_loss_events.same_action') }}</span>
        </RuiTooltip>
      </template>
      <template #item.type="{ row }">
        <ProfitLossEventType :type="row.type" />
      </template>
      <template #item.location="{ row }">
        <LocationDisplay :identifier="row.location" />
      </template>
      <template #item.timestamp="{ row }">
        <DateDisplay :timestamp="row.timestamp" />
      </template>
      <template #item.free_amount="{ row }">
        <div class="flex items-center justify-between flex-nowrap gap-4">
          <AssetLink
            v-if="row.assetIdentifier"
            :asset="row.assetIdentifier"
            link
          >
            <AssetIcon
              class="flex"
              :identifier="row.assetIdentifier"
              size="24px"
            />
          </AssetLink>
          <AmountDisplay
            force-currency
            :value="row.freeAmount"
            :asset="row.assetIdentifier ? row.assetIdentifier : ''"
          />
        </div>
      </template>
      <template #item.taxable_amount="{ row }">
        <AmountDisplay
          force-currency
          :value="row.taxableAmount"
          :asset="row.assetIdentifier ? row.assetIdentifier : ''"
        />
      </template>
      <template #item.price="{ row }">
        <AmountDisplay
          force-currency
          :value="row.price"
          show-currency="symbol"
          :fiat-currency="report.settings.profitCurrency"
        />
      </template>
      <template #item.pnl_taxable="{ row }">
        <AmountDisplay
          pnl
          force-currency
          :value="row.pnlTaxable"
          show-currency="symbol"
          :fiat-currency="report.settings.profitCurrency"
        />
      </template>
      <template #item.pnl_free="{ row }">
        <AmountDisplay
          pnl
          force-currency
          :value="row.pnlFree"
          show-currency="symbol"
          :fiat-currency="report.settings.profitCurrency"
        />
      </template>
      <template
        v-if="showUpgradeMessage"
        #body.prepend="{ colspan }"
      >
        <UpgradeRow
          events
          :total="report.totalActions"
          :limit="report.processedActions"
          :time-end="report.lastProcessedTimestamp"
          :time-start="report.firstProcessedTimestamp"
          :colspan="colspan"
          :label="t('common.events')"
        />
      </template>
      <template #item.notes="{ row }">
        <div class="py-1">
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

<style module lang="scss">
.group {
  @apply relative h-full w-2.5 ml-6;

  &__dot {
    @apply absolute left-1/2 top-1/2 transform -translate-x-1/2 -translate-y-1/2 w-2.5 h-2.5 rounded-full bg-rui-primary;
  }

  &__line {
    @apply absolute h-1/2 left-1/2 w-0 transform -translate-x-1/2 border-l-2 border-dashed border-rui-primary;

    &-top {
      @apply top-0;
    }

    &-bottom {
      @apply bottom-0;
    }
  }
}
</style>
