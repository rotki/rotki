<script setup lang="ts">
import type { DataTableColumn, DataTableSortData } from '@rotki/ui-library';
import type { CostBasis, MatchedAcquisitions, MatchedAcquisitionsEvent } from '@/types/reports';
import AmountDisplay from '@/components/display/amount/AmountDisplay.vue';
import DateDisplay from '@/components/display/DateDisplay.vue';
import SuccessDisplay from '@/components/display/SuccessDisplay.vue';
import { TableId, useRememberTableSorting } from '@/modules/table/use-remember-table-sorting';

type Acquisition = Omit<MatchedAcquisitions, 'event'> & MatchedAcquisitionsEvent;

const props = withDefaults(
  defineProps<{
    costBasis: CostBasis;
    currency?: string | null;
    showGroupLine?: boolean;
  }>(),
  {
    currency: null,
    showGroupLine: false,
  },
);

const { t } = useI18n({ useScope: 'global' });

const { costBasis, currency } = toRefs(props);

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
      currency: get(currency),
    }),
    sortable: true,
  },
  {
    align: 'end',
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
  const acquisitions = get(costBasis).matchedAcquisitions;
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
      class="absolute w-0.5 -top-4 -bottom-4 left-[0.8125rem]"
    >
      <div class="border-l-2 border-dashed border-rui-primary h-full transform -translate-x-1/2" />
    </div>

    <div
      :class="{ 'pl-[2.125rem]': showGroupLine }"
      class="grow"
    >
      <div class="flex pb-4 items-center gap-4">
        <p class="text-body-1 mb-0">
          {{ t('cost_basis_table.cost_basis') }}
        </p>
        <RuiChip
          v-if="costBasis.isComplete"
          size="sm"
          color="success"
        >
          {{ t('cost_basis_table.complete') }}
        </RuiChip>
        <RuiChip
          v-else
          size="sm"
          color="error"
        >
          {{ t('cost_basis_table.incomplete') }}
        </RuiChip>
      </div>
      <RuiCard
        variant="flat"
        no-padding
      >
        <RuiDataTable
          v-model:sort="sort"
          :rows="matchedAcquisitions"
          :cols="cols"
          row-attr="amount"
          outlined
        >
          <template #item.amount="{ row }">
            <AmountDisplay
              force-currency
              :value="row.amount"
            />
          </template>
          <template #item.fullAmount="{ row }">
            <AmountDisplay
              force-currency
              :value="row.fullAmount"
            />
          </template>
          <template #item.remainingAmount="{ row }">
            <AmountDisplay
              force-currency
              :value="row.fullAmount.minus(row.amount)"
            />
          </template>
          <template #item.rate="{ row }">
            <AmountDisplay
              force-currency
              :value="row.rate"
              show-currency="symbol"
              :fiat-currency="currency"
            />
          </template>
          <template #item.timestamp="{ row }">
            <DateDisplay :timestamp="row.timestamp" />
          </template>
          <template #item.taxable="{ row }">
            <SuccessDisplay :success="row.taxable" />
          </template>
        </RuiDataTable>
      </RuiCard>
    </div>
  </div>
</template>
