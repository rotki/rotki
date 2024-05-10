<script setup lang="ts">
import type { BaseDefiBalance } from '@/types/defi/lending';
import type { DataTableColumn, DataTableSortData } from '@rotki/ui-library-compat';

withDefaults(
  defineProps<{
    assets: BaseDefiBalance[];
    loading?: boolean;
  }>(),
  {
    loading: false,
  },
);

const { currencySymbol } = storeToRefs(useGeneralSettingsStore());
const { t } = useI18n();

const sort: Ref<DataTableSortData> = ref({
  column: 'usdValue',
  direction: 'desc' as const,
});

const headers = computed<DataTableColumn[]>(() => [
  {
    label: t('common.asset'),
    key: 'asset',
    sortable: true,
  },
  {
    label: t('common.amount'),
    key: 'amount',
    align: 'end',
    sortable: true,
  },
  { label: '', key: 'usdValue', align: 'end', sortable: true },
  {
    label: t('lending_asset_table.headers.effective_interest_rate'),
    key: 'effectiveInterestRate',
    align: 'end',
    sortable: true,
  },
]);
</script>

<template>
  <RuiDataTable
    :rows="assets"
    :cols="headers"
    :loading="loading"
    :sort.sync="sort"
    row-attr="asset"
    dense
    outlined
  >
    <template #item.asset="{ row }">
      <AssetDetails
        :asset="row.asset"
        hide-name
      />
    </template>
    <template #item.amount="{ row }">
      <AmountDisplay :value="row.amount" />
    </template>
    <template #item.usdValue="{ row }">
      <AmountDisplay
        fiat-currency="USD"
        :value="row.usdValue"
        show-currency="symbol"
      />
    </template>
    <template #item.effectiveInterestRate="{ row }">
      <PercentageDisplay :value="row.effectiveInterestRate" />
    </template>
    <template #header.text.usdValue>
      {{
        t('lending_asset_table.headers.usd_value', {
          currency: currencySymbol,
        })
      }}
    </template>
  </RuiDataTable>
</template>
