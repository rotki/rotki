<script setup lang="ts">
import type { HistoricalPrice } from '@/modules/assets/prices/price-types';
import type { TableEmptyState } from '@/modules/core/table/use-table-empty-state';
import type { RowDeleteQuestion } from '@/modules/shell/components/row-delete-question';
import { type DataTableColumn, type DataTableSortData, RuiDataTable } from '@rotki/ui-library';
import { computed, ref } from 'vue';
import { useI18n } from 'vue-i18n';
import { AssetAmountDisplay } from '@/modules/assets/amount-display/components';
import AssetDetails from '@/modules/assets/AssetDetails.vue';
import { priceDecimals } from '@/modules/assets/prices/price-decimals';
import { TableId, useRememberTableSorting } from '@/modules/core/table/use-remember-table-sorting';
import DateDisplay from '@/modules/shell/components/display/DateDisplay.vue';
import RowActions from '@/modules/shell/components/RowActions.vue';

const { disabled = false, emptyState, loading = false, rows } = defineProps<{
  /** turns the row actions off */
  disabled?: boolean;
  /** what the table shows when it has no rows */
  emptyState: TableEmptyState;
  loading?: boolean;
  rows: HistoricalPrice[];
}>();

const emit = defineEmits<{
  /** a row's delete was confirmed */
  delete: [item: HistoricalPrice];
  edit: [item: HistoricalPrice];
}>();

const { t } = useI18n({ useScope: 'global' });

const sort = ref<DataTableSortData<HistoricalPrice>>([
  {
    column: 'timestamp',
    direction: 'desc' as const,
  },
]);

const headers = computed<DataTableColumn<HistoricalPrice>[]>(() => [
  {
    key: 'fromAsset',
    label: t('price_table.headers.from_asset'),
    sortable: true,
  },
  // one amount, "0.03271 EUR", where "was worth", a number, an asset and "on" split one sentence
  {
    align: 'end',
    key: 'price',
    label: t('common.price'),
    sortable: true,
  },
  {
    key: 'timestamp',
    label: t('common.datetime'),
    sortable: true,
  },
  {
    align: 'end',
    class: 'w-12',
    key: 'actions',
    label: '',
  },
]);

useRememberTableSorting<HistoricalPrice>(TableId.HISTORIC_PRICES, sort, headers);

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
    row-attr="fromAsset"
    data-testid="historic-price-table"
  >
    <template #item.fromAsset="{ row }">
      <AssetDetails :asset="row.fromAsset" />
    </template>
    <template #item.timestamp="{ row }">
      <DateDisplay :timestamp="row.timestamp" />
    </template>
    <template #item.price="{ row }">
      <AssetAmountDisplay
        :amount="row.price"
        :asset="row.toAsset"
        :decimals="priceDecimals(row.price)"
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
