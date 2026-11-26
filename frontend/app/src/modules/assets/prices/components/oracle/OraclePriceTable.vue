<script setup lang="ts">
import type { OraclePriceEntry } from '@/modules/assets/prices/price-types';
import type { TableEmptyState } from '@/modules/core/table/use-table-empty-state';
import type { RowDeleteQuestion } from '@/modules/shell/components/row-delete-question';
import { type DataTableColumn, RuiChip, RuiDataTable, type TablePaginationData } from '@rotki/ui-library';
import { computed } from 'vue';
import { useI18n } from 'vue-i18n';
import { AssetAmountDisplay } from '@/modules/assets/amount-display/components';
import AssetDetails from '@/modules/assets/AssetDetails.vue';
import { getOracleSourceLabel } from '@/modules/assets/prices/oracle-source-labels';
import { priceDecimals } from '@/modules/assets/prices/price-decimals';
import { PriceOracle } from '@/modules/settings/types/price-oracle';
import DateDisplay from '@/modules/shell/components/display/DateDisplay.vue';
import RowActions from '@/modules/shell/components/RowActions.vue';

/** The server-side page, owned by the caller's server table. */
const pagination = defineModel<TablePaginationData>('pagination', { required: true });

const { disabled = false, emptyState, loading = false, rows } = defineProps<{
  /** turns the row actions off */
  disabled?: boolean;
  /** what the table shows when it has no rows */
  emptyState: TableEmptyState;
  loading?: boolean;
  rows: OraclePriceEntry[];
}>();

const emit = defineEmits<{
  /** a row's delete was confirmed */
  delete: [item: OraclePriceEntry];
  edit: [item: OraclePriceEntry];
}>();

const { t } = useI18n({ useScope: 'global' });

const headers = computed<DataTableColumn<OraclePriceEntry>[]>(() => [
  {
    key: 'fromAsset',
    label: t('price_table.headers.from_asset'),
  },
  // one amount, "0.03271 EUR", rather than a number and a two-line asset that doubled each row
  {
    align: 'end',
    key: 'price',
    label: t('common.price'),
  },
  {
    key: 'sourceType',
    label: t('oracle_prices.headers.source'),
  },
  {
    key: 'timestamp',
    label: t('common.datetime'),
  },
  {
    align: 'end',
    class: 'w-12',
    key: 'actions',
    label: '',
  },
]);

const sourceBrandColors: Record<string, string> = {
  [PriceOracle.ALCHEMY]: '#363ff9',
  [PriceOracle.BIRDEYE]: '#ff6d00',
  [PriceOracle.COINGECKO]: '#8dc63f',
  [PriceOracle.COINBASE]: '#0052ff',
  [PriceOracle.CRYPTOCOMPARE]: '#f37021',
  [PriceOracle.DEFILLAMA]: '#2172e5',
  [PriceOracle.FIAT]: '#85bb65',
  [PriceOracle.MORALIS]: '#1ac6ff',
  [PriceOracle.UNISWAP2]: '#ff007a',
  [PriceOracle.UNISWAP3]: '#e50887',
};

type ChipColor = 'grey' | 'primary' | 'secondary' | 'error' | 'warning' | 'info' | 'success';

const sourceContextColors: Record<string, ChipColor> = {
  [PriceOracle.BLOCKCHAIN]: 'secondary',
  [PriceOracle.MANUAL]: 'warning',
  [PriceOracle.MANUALCURRENT]: 'warning',
};

function getSourceBgColor(source: string): string | undefined {
  return sourceBrandColors[source];
}

function getSourceColor(source: string): ChipColor {
  return sourceContextColors[source] ?? 'grey';
}

const deleteConfirm = computed<RowDeleteQuestion>(() => ({
  message: t('oracle_prices.delete.dialog.message'),
  title: t('oracle_prices.delete.dialog.title'),
}));
</script>

<template>
  <RuiDataTable
    v-model:pagination.external="pagination"
    dense
    :cols="headers"
    :empty="emptyState"
    :loading="loading"
    :rows="rows"
    row-attr="fromAsset"
    data-testid="oracle-price-table"
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
    <template #item.sourceType="{ row }">
      <RuiChip
        size="sm"
        variant="tonal"
        :color="getSourceColor(row.sourceType)"
      >
        <span class="inline-flex items-center gap-1.5">
          <span
            v-if="getSourceBgColor(row.sourceType)"
            class="size-2 rounded-full shrink-0"
            :style="{ backgroundColor: getSourceBgColor(row.sourceType) }"
          />
          {{ getOracleSourceLabel(row.sourceType) }}
        </span>
      </RuiChip>
    </template>
    <template #item.actions="{ row }">
      <RowActions
        align="end"
        :disabled="disabled"
        :delete-tooltip="t('oracle_prices.actions.delete.tooltip')"
        :edit-tooltip="t('oracle_prices.actions.edit.tooltip')"
        :delete-confirm="deleteConfirm"
        @delete-click="emit('delete', row)"
        @edit-click="emit('edit', row)"
      />
    </template>
  </RuiDataTable>
</template>
