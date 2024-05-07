<script setup lang="ts">
import { some } from 'lodash-es';
import { isTransactionEvent } from '@/utils/report';
import type { DataTableColumn, DataTableOptions, DataTableSortData } from '@rotki/ui-library-compat';
import type { ProfitLossEvent, ProfitLossEvents, SelectedReport } from '@/types/reports';

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
  (
    e: 'update:page',
    page: { reportId: number; offset: number; limit: number }
  ): void;
}>();

const { t } = useI18n();

type PnLItem = ProfitLossEvent & { id: number };

const { report } = toRefs(props);

const tablePagination = ref<DataTableOptions['pagination']>();
const expanded = ref([]);

const sort: Ref<DataTableSortData> = ref({
  column: 'time',
  direction: 'asc' as const,
});

const route = useRoute();
const { getChain } = useSupportedChains();

const tableHeaders = computed<DataTableColumn[]>(() => [
  {
    label: '',
    key: 'group',
    class: '!p-0',
    cellClass: '!p-0 h-px',
  },
  {
    label: '',
    key: 'expand',
  },
  {
    label: t('common.type'),
    key: 'type',
    align: 'center',
    class: 'w-[6.875rem]',
  },
  {
    label: t('common.location'),
    key: 'location',
    align: 'center',
    class: 'w-[7.5rem]',
    cellClass: 'py-2',
  },
  {
    label: t('profit_loss_events.headers.tax_free_amount'),
    key: 'free_amount',
    align: 'end',
  },
  {
    label: t('profit_loss_events.headers.taxable_amount'),
    key: 'taxable_amount',
    align: 'end',
  },
  {
    label: t('common.price'),
    key: 'price',
    align: 'end',
  },
  {
    label: t('profit_loss_events.headers.pnl_free'),
    key: 'pnl_free',
    align: 'end',
  },
  {
    label: t('profit_loss_events.headers.pnl_taxable'),
    key: 'pnl_taxable',
    align: 'end',
  },
  {
    label: t('common.datetime'),
    key: 'time',
  },
  {
    label: t('common.notes'),
    key: 'notes',
  },
  {
    label: t('common.actions_text'),
    key: 'actions',
    align: 'end',
    class: 'w-[8.75rem]',
  },
]);

const items = computed<PnLItem[]>(() => get(report).entries.map((value, index) => ({
  ...value,
  id: index,
  groupLine: checkGroupLine(get(report).entries, index),
})));

const itemLength = computed(() => {
  const { entriesFound, entriesLimit } = report.value;
  if (entriesLimit > 0 && entriesLimit <= entriesFound)
    return entriesLimit;

  return entriesFound;
});

const premium = usePremium();

const showUpgradeMessage = computed(
  () =>
    !premium.value && report.value.totalActions > report.value.processedActions,
);

function updatePagination(tableOptions: DataTableOptions) {
  const { pagination } = tableOptions;
  set(tablePagination, pagination);

  if (!pagination)
    return;

  const { page, limit } = pagination;

  const reportId = Number.parseInt(get(route).params.id as string);

  emit('update:page', {
    reportId,
    limit,
    offset: limit * (page - 1),
  });
}

function checkGroupLine(entries: ProfitLossEvents, index: number) {
  const current = entries[index];
  const prev = index - 1 >= 0 ? entries[index - 1] : null;
  const next = index + 1 < entries.length ? entries[index + 1] : null;

  return {
    top: !!(current?.groupId && prev && current?.groupId === prev?.groupId),
    bottom: !!(current?.groupId && next && current?.groupId === next?.groupId),
  };
}

function isExpanded(id: number) {
  return some(get(expanded), { id });
}

function expand(item: PnLItem) {
  set(expanded, isExpanded(item.id) ? [] : [item]);
}

const css = useCssModule();
</script>

<template>
  <RuiCard>
    <template #header>
      {{ t('common.events') }}
    </template>
    <RuiDataTable
      :cols="tableHeaders"
      :rows="items"
      :loading="loading || refreshing"
      :expanded.sync="expanded"
      :pagination="{
        limit: tablePagination?.limit ?? 10,
        page: tablePagination?.page ?? 1,
        total: itemLength,
      }"
      :pagination-modifiers="{ external: true }"
      :sort.sync="sort"
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
            <div :class="css.group">
              <div
                v-if="row.groupLine.top"
                :class="[css.group__line, css['group__line-top']]"
              />
              <div :class="css.group__dot" />
              <div
                v-if="row.groupLine.bottom"
                :class="[css.group__line, css['group__line-bottom']]"
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
      <template #item.time="{ row }">
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
            :amount="
              row.taxableAmount.isZero() ? row.freeAmount : row.taxableAmount
            "
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

          {{
            isExpanded(row.id)
              ? t('profit_loss_events.cost_basis.hide')
              : t('profit_loss_events.cost_basis.show')
          }}
        </RuiTooltip>
      </template>
      <template #expanded-item="{ row }">
        <CostBasisTable
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
  height: 100%;
  position: relative;
  width: 10px;
  margin-left: 1.5rem;

  &__dot {
    position: absolute;
    left: 50%;
    top: 50%;
    transform: translate(-50%, -50%);
    width: 10px;
    height: 10px;
    border-radius: 10px;
    background: var(--v-primary-base);
  }

  &__line {
    position: absolute;
    height: 50%;
    left: 50%;
    width: 0;
    transform: translateX(-50%);
    border-left: 2px dashed var(--v-primary-base);

    &-top {
      top: 0;
    }

    &-bottom {
      bottom: 0;
    }
  }
}
</style>
