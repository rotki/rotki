<script setup lang="ts">
import type { DataTableColumn } from '@rotki/ui-library';
import type { OraclePriceEntry, OraclePricesQuery } from '@/modules/assets/prices/price-types';
import { ValueDisplay } from '@/modules/assets/amount-display/components';
import AssetDetails from '@/modules/assets/AssetDetails.vue';
import OraclePriceEditDialog from '@/modules/assets/prices/components/oracle/OraclePriceEditDialog.vue';
import { useOraclePrices } from '@/modules/assets/prices/use-oracle-prices';
import { type Filters, type Matcher, useOraclePricesFilter } from '@/modules/assets/prices/use-oracle-prices-filter';
import { useConfirmStore } from '@/modules/core/common/use-confirm-store';
import TableFilter from '@/modules/core/table/TableFilter.vue';
import { usePaginationFilters } from '@/modules/core/table/use-pagination-filter';
import { PriceOracle } from '@/modules/settings/types/price-oracle';
import DateDisplay from '@/modules/shell/components/display/DateDisplay.vue';
import RowActions from '@/modules/shell/components/RowActions.vue';

const { t } = useI18n({ useScope: 'global' });

const { deletePrice, fetchData } = useOraclePrices();

const {
  fetchData: refresh,
  filters,
  isLoading: loading,
  matchers,
  pagination,
  state,
} = usePaginationFilters<
  OraclePriceEntry,
  OraclePricesQuery,
  Filters,
  Matcher
>(fetchData, {
  defaultSortBy: {
    column: 'timestamp',
    direction: 'desc',
  },
  filterSchema: useOraclePricesFilter,
});

const headers = computed<DataTableColumn<OraclePriceEntry>[]>(() => [
  {
    key: 'fromAsset',
    label: t('price_table.headers.from_asset'),
  },
  {
    align: 'end',
    key: 'price',
    label: t('common.price'),
  },
  {
    key: 'toAsset',
    label: t('price_table.headers.to_asset'),
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
    class: 'w-[3rem]',
    key: 'actions',
    label: '',
  },
]);

const sourceLabels: Record<string, string> = {
  [PriceOracle.ALCHEMY]: 'Alchemy',
  [PriceOracle.BLOCKCHAIN]: 'Blockchain',
  [PriceOracle.COINGECKO]: 'CoinGecko',
  [PriceOracle.CRYPTOCOMPARE]: 'CryptoCompare',
  [PriceOracle.DEFILLAMA]: 'DefiLlama',
  [PriceOracle.FIAT]: 'Fiat',
  [PriceOracle.MANUAL]: 'Manual',
  [PriceOracle.UNISWAP2]: 'Uniswap V2',
  [PriceOracle.UNISWAP3]: 'Uniswap V3',
};

const sourceBrandColors: Record<string, string> = {
  [PriceOracle.ALCHEMY]: '#363ff9',
  [PriceOracle.COINGECKO]: '#8dc63f',
  [PriceOracle.CRYPTOCOMPARE]: '#f37021',
  [PriceOracle.DEFILLAMA]: '#2172e5',
  [PriceOracle.FIAT]: '#85bb65',
  [PriceOracle.UNISWAP2]: '#ff007a',
  [PriceOracle.UNISWAP3]: '#e50887',
};

type ChipColor = 'grey' | 'primary' | 'secondary' | 'error' | 'warning' | 'info' | 'success';

const sourceContextColors: Record<string, ChipColor> = {
  [PriceOracle.BLOCKCHAIN]: 'secondary',
  [PriceOracle.MANUAL]: 'warning',
  [PriceOracle.MANUALCURRENT]: 'warning',
};

function getSourceLabel(source: string): string {
  return sourceLabels[source] ?? source;
}

function getSourceBgColor(source: string): string | undefined {
  return sourceBrandColors[source];
}

function getSourceColor(source: string): ChipColor {
  return sourceContextColors[source] ?? 'grey';
}

const editingItem = ref<OraclePriceEntry>();

function startEdit(item: OraclePriceEntry): void {
  set(editingItem, { ...item });
}

const { show } = useConfirmStore();

function showDeleteConfirmation(item: OraclePriceEntry): void {
  show(
    {
      message: t('oracle_prices.delete.dialog.message'),
      title: t('oracle_prices.delete.dialog.title'),
    },
    async () => {
      const deleted = await deletePrice(item);
      if (deleted)
        await refresh();
    },
  );
}

onMounted(async () => {
  await refresh();
});
</script>

<template>
  <div class="flex flex-col gap-4">
    <RuiCard>
      <div class="flex items-center justify-between gap-3 mb-4">
        <RuiTooltip :open-delay="400">
          <template #activator>
            <RuiButton
              variant="outlined"
              color="primary"
              :loading="loading"
              @click="refresh()"
            >
              <template #prepend>
                <RuiIcon name="lu-refresh-ccw" />
              </template>
              {{ t('common.refresh') }}
            </RuiButton>
          </template>
          {{ t('oracle_prices.refresh_tooltip') }}
        </RuiTooltip>
        <div class="w-full sm:max-w-[25rem]">
          <TableFilter
            v-model:matches="filters"
            :matchers="matchers"
          />
        </div>
      </div>

      <RuiDataTable
        v-model:pagination.external="pagination"
        outlined
        dense
        :cols="headers"
        :loading="loading"
        :rows="state.data"
        row-attr="fromAsset"
      >
        <template #item.fromAsset="{ row }">
          <AssetDetails :asset="row.fromAsset" />
        </template>
        <template #item.toAsset="{ row }">
          <AssetDetails :asset="row.toAsset" />
        </template>
        <template #item.timestamp="{ row }">
          <DateDisplay :timestamp="row.timestamp" />
        </template>
        <template #item.price="{ row }">
          <ValueDisplay :value="row.price" />
        </template>
        <template #item.sourceType="{ row }">
          <RuiChip
            size="sm"
            :bg-color="getSourceBgColor(row.sourceType)"
            :text-color="getSourceBgColor(row.sourceType) ? '#ffffff' : undefined"
            :variant="getSourceBgColor(row.sourceType) ? 'filled' : 'outlined'"
            :color="getSourceColor(row.sourceType)"
          >
            {{ getSourceLabel(row.sourceType) }}
          </RuiChip>
        </template>
        <template #item.actions="{ row }">
          <RowActions
            :disabled="loading"
            :delete-tooltip="t('oracle_prices.actions.delete.tooltip')"
            :edit-tooltip="t('oracle_prices.actions.edit.tooltip')"
            @delete-click="showDeleteConfirmation(row)"
            @edit-click="startEdit(row)"
          />
        </template>
      </RuiDataTable>
    </RuiCard>

    <OraclePriceEditDialog
      v-model="editingItem"
      @refresh="refresh()"
    />
  </div>
</template>
