<script setup lang="ts">
import type { DataTableColumn, DataTableSortData } from '@rotki/ui-library';
import type { CostBasis, MatchedAcquisitions, MatchedAcquisitionsEvent } from '@/modules/reports/report-types';
import { FiatDisplay, ValueDisplay } from '@/modules/assets/amount-display/components';
import { TableId, useRememberTableSorting } from '@/modules/core/table/use-remember-table-sorting';
import DateDisplay from '@/modules/shell/components/display/DateDisplay.vue';
import SuccessDisplay from '@/modules/shell/components/display/SuccessDisplay.vue';

type Acquisition = Omit<MatchedAcquisitions, 'event'> & MatchedAcquisitionsEvent;

const {
  costBasis,
  currency = null,
  showGroupLine = false,
} = defineProps<{
  costBasis: CostBasis;
  currency?: string | null;
  showGroupLine?: boolean;
}>();

const { t } = useI18n({ useScope: 'global' });

const sort = ref<DataTableSortData<Acquisition>>({
  column: 'timestamp',
  direction: 'asc',
});

const cols = computed<DataTableColumn<Acquisition>[]>(() => [
  {
    align: 'end',
    key: 'amount',
    label: t('cost_basis_table.headers.amount'),
    sortable: true,
  },
  {
    align: 'end',
    key: 'fullAmount',
    label: t('cost_basis_table.headers.full_amount'),
    sortable: true,
  },
  {
    align: 'end',
    key: 'remainingAmount',
    label: t('cost_basis_table.headers.remaining_amount'),
    sortable: true,
  },
  {
    align: 'end',
    key: 'rate',
    label: t('cost_basis_table.headers.rate', {
      currency,
    }),
    sortable: true,
  },
  {
    align: 'end',
    cellClass: 'whitespace-nowrap',
    key: 'timestamp',
    label: t('common.datetime'),
    sortable: true,
  },
  {
    key: 'taxable',
    label: t('cost_basis_table.headers.taxable'),
    sortable: true,
  },
]);

useRememberTableSorting<Acquisition>(TableId.COST_BASIS, sort, cols);

const matchedAcquisitions = computed<Acquisition[]>(() => {
  const acquisitions = costBasis.matchedAcquisitions;
  if (!acquisitions)
    return [];

  return acquisitions.map((acquisition) => {
    const { event, ...rest } = acquisition;

    return {
      ...rest,
      ...event,
    };
  });
});
</script>

<template>
  <div class="relative">
    <div
      v-if="showGroupLine"
      class="absolute w-0.5 -top-4 -bottom-4 left-3.25"
    >
      <div class="border-l-2 border-dashed border-rui-primary h-full transform -translate-x-1/2" />
    </div>

    <div
      :class="{ 'pl-8.5': showGroupLine }"
      class="grow"
    >
      <div class="flex pb-3 items-center gap-3">
        <h3 class="text-sm font-medium text-rui-text">
          {{ t('cost_basis_table.cost_basis') }}
        </h3>
        <RuiChip
          size="sm"
          variant="tonal"
          :color="costBasis.isComplete ? 'success' : 'error'"
          data-testid="cost-basis-status"
        >
          {{ costBasis.isComplete ? t('cost_basis_table.complete') : t('cost_basis_table.incomplete') }}
        </RuiChip>
      </div>
      <div>
        <RuiDataTable
          v-model:sort="sort"
          :rows="matchedAcquisitions"
          :cols="cols"
          row-attr="amount"
          outlined
          dense
        >
          <template #item.amount="{ row }">
            <ValueDisplay :value="row.amount" />
          </template>
          <template #item.fullAmount="{ row }">
            <ValueDisplay :value="row.fullAmount" />
          </template>
          <template #item.remainingAmount="{ row }">
            <ValueDisplay :value="row.fullAmount.minus(row.amount)" />
          </template>
          <template #item.rate="{ row }">
            <FiatDisplay
              :value="row.rate"
              :currency="currency ?? undefined"
            />
          </template>
          <template #item.timestamp="{ row }">
            <DateDisplay :timestamp="row.timestamp" />
          </template>
          <template #item.taxable="{ row }">
            <SuccessDisplay :success="row.taxable" />
          </template>
        </RuiDataTable>
      </div>
    </div>
  </div>
</template>
