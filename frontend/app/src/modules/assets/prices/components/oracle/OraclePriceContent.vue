<script setup lang="ts">
import type { DataTableColumn } from '@rotki/ui-library';
import type { OraclePriceEntry, OraclePricesQuery } from '@/modules/assets/prices/price-types';
import { ValueDisplay } from '@/modules/assets/amount-display/components';
import AssetDetails from '@/modules/assets/AssetDetails.vue';
import OraclePriceEditDialog from '@/modules/assets/prices/components/oracle/OraclePriceEditDialog.vue';
import { getOracleSourceLabel } from '@/modules/assets/prices/oracle-source-labels';
import { useOraclePriceFields } from '@/modules/assets/prices/use-oracle-price-fields';
import { useOraclePrices } from '@/modules/assets/prices/use-oracle-prices';
import { type Filters, useOraclePricesFilter } from '@/modules/assets/prices/use-oracle-prices-filter';
import { useConfirmStore } from '@/modules/core/common/use-confirm-store';
import { usePillBarLabels } from '@/modules/core/table/pill/composables/use-pill-bar-labels';
import PillFilterBar from '@/modules/core/table/pill/PillFilterBar.vue';
import { useServerTable } from '@/modules/core/table/use-server-table';
import { PriceOracle } from '@/modules/settings/types/price-oracle';
import DateDisplay from '@/modules/shell/components/display/DateDisplay.vue';
import RowActions from '@/modules/shell/components/RowActions.vue';

const { t } = useI18n({ useScope: 'global' });

const { deletePrice, fetchData } = useOraclePrices();

const filterSchema = useOraclePricesFilter();
const fields = useOraclePriceFields();
const pillLabels = usePillBarLabels();

const {
  collection,
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
  filterSchema,
  sort: {
    default: {
      column: 'timestamp',
      direction: 'desc',
    },
  },
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

const sourceBrandColors: Record<string, string> = {
  [PriceOracle.ALCHEMY]: '#363ff9',
  [PriceOracle.COINGECKO]: '#8dc63f',
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
        <PillFilterBar
          v-model:matches="filter"
          class="flex-1 min-w-[12rem] md:min-w-[24rem]"
          :fields="fields"
          :labels="pillLabels"
        />
      </div>

      <RuiDataTable
        v-model:pagination.external="pagination"
        outlined
        dense
        :cols="headers"
        :loading="loading"
        :rows="collection.data"
        row-attr="fromAsset"
        data-testid="oracle-price-table"
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
            {{ getOracleSourceLabel(row.sourceType) }}
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
