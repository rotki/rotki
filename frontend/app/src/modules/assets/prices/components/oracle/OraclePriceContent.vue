<script setup lang="ts">
import type { DataTableColumn } from '@rotki/ui-library';
import type { OraclePriceEntry, OraclePricesQuery } from '@/modules/assets/prices/price-types';
import type { Filters } from '@/modules/assets/prices/use-oracle-prices-filter';
import { AssetAmountDisplay } from '@/modules/assets/amount-display/components';
import AssetDetails from '@/modules/assets/AssetDetails.vue';
import OraclePriceEditDialog from '@/modules/assets/prices/components/oracle/OraclePriceEditDialog.vue';
import { getOracleSourceLabel } from '@/modules/assets/prices/oracle-source-labels';
import { priceDecimals } from '@/modules/assets/prices/price-decimals';
import { useOraclePriceFields } from '@/modules/assets/prices/use-oracle-price-fields';
import { useOraclePrices } from '@/modules/assets/prices/use-oracle-prices';
import { useConfirmStore } from '@/modules/core/common/use-confirm-store';
import { usePillBarLabels } from '@/modules/core/table/pill/composables/use-pill-bar-labels';
import PillFilterBar from '@/modules/core/table/pill/PillFilterBar.vue';
import TableFrame from '@/modules/core/table/TableFrame.vue';
import { useServerTable } from '@/modules/core/table/use-server-table';
import { useTableEmptyState } from '@/modules/core/table/use-table-empty-state';
import { PriceOracle } from '@/modules/settings/types/price-oracle';
import DateDisplay from '@/modules/shell/components/display/DateDisplay.vue';
import HintMenuIcon from '@/modules/shell/components/HintMenuIcon.vue';
import RowActions from '@/modules/shell/components/RowActions.vue';

defineSlots<{
  /** the page's tab switch, at the start of the toolbar */
  tabs?: () => any;
}>();

const { t } = useI18n({ useScope: 'global' });

const { deletePrice, fetchData } = useOraclePrices();

const fields = useOraclePriceFields();
const pillLabels = usePillBarLabels();

const {
  collection,
  error,
  filter,
  isLoading: loading,
  pagination,
  refetch: refresh,
} = useServerTable<
  OraclePriceEntry,
  OraclePricesQuery,
  Filters
>({
  fetch: fetchData,
  fields,
  sort: {
    default: {
      column: 'timestamp',
      direction: 'desc',
    },
  },
});

const emptyState = useTableEmptyState({ error });

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

// for the page header's refresh button
defineExpose({
  loading,
  refresh,
});
</script>

<template>
  <div class="flex flex-col gap-4">
    <TableFrame>
      <template #toolbar>
        <slot name="tabs" />
        <HintMenuIcon>
          {{ t('oracle_prices.hint') }}
        </HintMenuIcon>
        <PillFilterBar
          v-model:matches="filter"
          class="flex-1 min-w-48 md:min-w-96"
          :fields="fields"
          :labels="pillLabels"
        />
      </template>

      <RuiDataTable
        v-model:pagination.external="pagination"
        dense
        :cols="headers"
        :empty="emptyState"
        :loading="loading"
        :rows="collection.data"
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
            :disabled="loading"
            :delete-tooltip="t('oracle_prices.actions.delete.tooltip')"
            :edit-tooltip="t('oracle_prices.actions.edit.tooltip')"
            @delete-click="showDeleteConfirmation(row)"
            @edit-click="startEdit(row)"
          />
        </template>
      </RuiDataTable>
    </TableFrame>

    <OraclePriceEditDialog
      v-model="editingItem"
      @refresh="refresh()"
    />
  </div>
</template>
