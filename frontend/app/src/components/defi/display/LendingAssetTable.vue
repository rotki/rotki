<script setup lang="ts">
import { useGeneralSettingsStore } from '@/store/settings/general';
import PercentageDisplay from '@/components/display/PercentageDisplay.vue';
import AmountDisplay from '@/components/display/amount/AmountDisplay.vue';
import AssetDetails from '@/components/helper/AssetDetails.vue';
import type { DataTableColumn, DataTableSortData } from '@rotki/ui-library';
import type { BaseDefiBalance } from '@/types/defi/lending';

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

const sort = ref<DataTableSortData<BaseDefiBalance>>({
  column: 'usdValue',
  direction: 'desc' as const,
});

const headers = computed<DataTableColumn<BaseDefiBalance>[]>(() => [
  {
    key: 'asset',
    label: t('common.asset'),
    sortable: true,
  },
  {
    align: 'end',
    key: 'amount',
    label: t('common.amount'),
    sortable: true,
  },
  { align: 'end', key: 'usdValue', label: '', sortable: true },
  {
    align: 'end',
    key: 'effectiveInterestRate',
    label: t('lending_asset_table.headers.effective_interest_rate'),
    sortable: true,
  },
]);
</script>

<template>
  <RuiDataTable
    v-model:sort="sort"
    :rows="assets"
    :cols="headers"
    :loading="loading"
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
