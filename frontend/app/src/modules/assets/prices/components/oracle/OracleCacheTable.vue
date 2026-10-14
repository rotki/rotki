<script setup lang="ts">
import type { DataTableColumn } from '@rotki/ui-library';
import type { OracleCacheMeta } from '@/modules/assets/prices/price-types';
import AssetDetails from '@/modules/assets/AssetDetails.vue';
import DateDisplay from '@/modules/shell/components/display/DateDisplay.vue';
import RowActions from '@/modules/shell/components/RowActions.vue';

type CacheRow = OracleCacheMeta & { id: number };

const { disabled = false, loading = false, rows } = defineProps<{
  disabled?: boolean;
  loading?: boolean;
  rows: CacheRow[];
}>();

const emit = defineEmits<{
  delete: [entry: CacheRow];
}>();

const { t } = useI18n({ useScope: 'global' });

const columns = computed<DataTableColumn<CacheRow>[]>(() => [
  {
    key: 'fromAsset',
    label: t('oracle_prices.cache.headers.from_asset'),
  },
  {
    key: 'toAsset',
    label: t('oracle_prices.cache.headers.to_asset'),
  },
  // one line per date, so a row is as tall as its two-line assets rather than its wrapped dates
  {
    cellClass: 'whitespace-nowrap',
    key: 'fromTimestamp',
    label: t('oracle_prices.cache.headers.from_date'),
  },
  {
    cellClass: 'whitespace-nowrap',
    key: 'toTimestamp',
    label: t('oracle_prices.cache.headers.to_date'),
  },
  {
    align: 'end',
    class: 'w-12',
    key: 'actions',
    label: '',
  },
]);
</script>

<template>
  <RuiDataTable
    dense
    :cols="columns"
    :loading="loading"
    :rows="rows"
    row-attr="id"
    :empty="{ label: t('oracle_prices.cache.dialog.empty') }"
    data-testid="oracle-cache-table"
  >
    <template #item.fromAsset="{ row }">
      <div class="max-w-56">
        <AssetDetails :asset="row.fromAsset" />
      </div>
    </template>
    <template #item.toAsset="{ row }">
      <div class="max-w-56">
        <AssetDetails :asset="row.toAsset" />
      </div>
    </template>
    <template #item.fromTimestamp="{ row }">
      <DateDisplay :timestamp="Number(row.fromTimestamp)" />
    </template>
    <template #item.toTimestamp="{ row }">
      <DateDisplay :timestamp="Number(row.toTimestamp)" />
    </template>
    <template #item.actions="{ row }">
      <RowActions
        align="end"
        no-edit
        :disabled="disabled"
        :delete-tooltip="t('oracle_prices.cache.delete.tooltip')"
        @delete-click="emit('delete', row)"
      />
    </template>
  </RuiDataTable>
</template>
