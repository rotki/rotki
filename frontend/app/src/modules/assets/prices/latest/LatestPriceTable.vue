<script setup lang="ts">
import type { ManualPriceWithUsd } from '@/modules/assets/prices/price-types';
import type { TableEmptyState } from '@/modules/core/table/use-table-empty-state';
import type { RowDeleteQuestion } from '@/modules/shell/components/row-delete-question';
import { type DataTableColumn, type DataTableSortData, RuiDataTable } from '@rotki/ui-library';
import { get } from '@vueuse/shared';
import { computed, ref } from 'vue';
import { useI18n } from 'vue-i18n';
import { AssetAmountDisplay, FiatDisplay } from '@/modules/assets/amount-display/components';
import AssetDetails from '@/modules/assets/AssetDetails.vue';
import { isNft } from '@/modules/assets/nft-utils';
import { priceDecimals } from '@/modules/assets/prices/price-decimals';
import NftDetails from '@/modules/balances/nft/NftDetails.vue';
import { TableId, useRememberTableSorting } from '@/modules/core/table/use-remember-table-sorting';
import { useSetting } from '@/modules/settings/use-setting';
import RowActions from '@/modules/shell/components/RowActions.vue';

const { disabled = false, emptyState, loading = false, rows } = defineProps<{
  /** turns the row actions off */
  disabled?: boolean;
  /** what the table shows when it has no rows */
  emptyState: TableEmptyState;
  loading?: boolean;
  rows: ManualPriceWithUsd[];
}>();

const emit = defineEmits<{
  /** a row's delete was confirmed */
  delete: [item: ManualPriceWithUsd];
  edit: [item: ManualPriceWithUsd];
}>();

const { t } = useI18n({ useScope: 'global' });

const currencySymbol = useSetting('currencySymbol');

const sort = ref<DataTableSortData<ManualPriceWithUsd>>([]);

const headers = computed<DataTableColumn<ManualPriceWithUsd>[]>(() => [
  {
    key: 'fromAsset',
    label: t('price_table.headers.from_asset'),
    sortable: true,
  },
  // one amount, "3,000.00 USDC", where an "is worth", a number and an asset column split one sentence
  {
    align: 'end',
    key: 'price',
    label: t('common.price'),
    sortable: true,
  },
  {
    align: 'end',
    key: 'usdPrice',
    label: t('common.price_in_symbol', { symbol: get(currencySymbol) }),
    sortable: true,
  },
  {
    align: 'end',
    class: 'w-12',
    key: 'actions',
    label: '',
  },
]);

useRememberTableSorting<ManualPriceWithUsd>(TableId.LATEST_PRICES, sort, headers);

const deleteConfirm = computed<RowDeleteQuestion>(() => ({
  message: t('price_table.delete.dialog.message'),
  title: t('price_table.delete.dialog.title'),
}));
</script>

<template>
  <RuiDataTable
    v-model:sort="sort"
    dense
    :cols="headers"
    :loading="loading"
    :rows="rows"
    :empty="emptyState"
    row-attr="id"
    data-testid="latest-price-table"
  >
    <template #item.fromAsset="{ row }">
      <NftDetails
        v-if="isNft(row.fromAsset)"
        :identifier="row.fromAsset"
      />
      <AssetDetails
        v-else
        class="[&_.avatar]:ml-1.5 [&_.avatar]:mr-2"
        :asset="row.fromAsset"
      />
    </template>
    <template #item.price="{ row }">
      <AssetAmountDisplay
        :amount="row.price"
        :asset="row.toAsset"
        :decimals="priceDecimals(row.price)"
      />
    </template>
    <template #item.usdPrice="{ row }">
      <FiatDisplay
        :value="row.usdPrice"
        :loading="!row.usdPrice || row.usdPrice.lt(0)"
        :price-asset="row.fromAsset"
        :format="{ decimals: row.usdPrice ? priceDecimals(row.usdPrice) : undefined }"
      />
    </template>
    <template #item.actions="{ row }">
      <RowActions
        align="end"
        :disabled="disabled"
        :delete-tooltip="t('price_table.actions.delete.tooltip')"
        :edit-tooltip="t('price_table.actions.edit.tooltip')"
        :delete-confirm="deleteConfirm"
        @delete-click="emit('delete', row)"
        @edit-click="emit('edit', row)"
      />
    </template>
  </RuiDataTable>
</template>
