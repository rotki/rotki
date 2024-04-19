<script setup lang="ts">
import type { CostBasis, MatchedAcquisitions, MatchedAcquisitionsEvent } from '@/types/reports';
import type { DataTableColumn, DataTableSortData } from '@rotki/ui-library-compat';

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

const { t } = useI18n();

const { costBasis, currency } = toRefs(props);

const sort = ref<DataTableSortData>({
  column: 'time',
  direction: 'asc' as const,
});

const css = useCssModule();

const cols = computed<DataTableColumn[]>(() => [
  {
    label: t('cost_basis_table.headers.amount'),
    key: 'amount',
    align: 'end',
    sortable: true,
  },
  {
    label: t('cost_basis_table.headers.full_amount'),
    key: 'fullAmount',
    align: 'end',
    sortable: true,
  },
  {
    label: t('cost_basis_table.headers.remaining_amount'),
    key: 'remainingAmount',
    align: 'end',
    sortable: true,
  },
  {
    label: t('cost_basis_table.headers.rate', {
      currency: get(currency),
    }),
    key: 'rate',
    align: 'end',
    sortable: true,
  },
  {
    label: t('common.datetime'),
    key: 'timestamp',
    align: 'end',
    sortable: true,
  },
  {
    label: t('cost_basis_table.headers.taxable'),
    key: 'taxable',
    sortable: true,
  },
]);

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
},
);
</script>

<template>
  <div
    class="relative"
  >
    <div
      v-if="showGroupLine"
      :class="css.group"
    >
      <div :class="css.group__line" />
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
          :class="css.table"
          :rows="matchedAcquisitions"
          :cols="cols"
          :sort.sync="sort"
          row-attr="id"
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

<style module lang="scss">
.group {
  position: absolute;
  width: 2px;
  top: -1rem;
  bottom: -1rem;
  left: .8125rem;

  &__line {
    height: 100%;
    transform: translateX(-50%);
    border-left: 2px dashed var(--v-primary-base);
  }
}
</style>
