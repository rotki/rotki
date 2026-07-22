<script setup lang="ts">
import type { AssetBalance } from '@rotki/common';
import type { DataTableColumn, DataTableSortData } from '@rotki/ui-library';
import type { ExchangeSavingsEvent, ExchangeSavingsRequestPayload } from '@/modules/balances/types/exchanges';
import { AssetValueDisplay, FiatDisplay, ValueDisplay } from '@/modules/assets/amount-display';
import AssetDetails from '@/modules/assets/AssetDetails.vue';
import { useBinanceSavings } from '@/modules/balances/exchanges/use-binance-savings';
import { Section } from '@/modules/core/common/status';
import { TableId, useRememberTableSorting } from '@/modules/core/table/use-remember-table-sorting';
import { useServerTable } from '@/modules/core/table/use-server-table';
import { useSetting } from '@/modules/settings/use-setting';
import DateDisplay from '@/modules/shell/components/display/DateDisplay.vue';
import RowAppend from '@/modules/shell/components/RowAppend.vue';
import { useSectionStatus } from '@/modules/shell/sync-progress/use-section-status';

const { exchange } = defineProps<{
  exchange: 'binance' | 'binanceus';
}>();

const { t } = useI18n({ useScope: 'global' });

const savingsAssets = ref<string[]>([]);
const savingsReceived = ref<AssetBalance[]>([]);

const { isLoading: loading } = useSectionStatus(Section.EXCHANGE_SAVINGS);
const { fetchExchangeSavings } = useBinanceSavings();
const currencySymbol = useSetting('currencySymbol');

const defaultParams = computed<Record<string, unknown>>(() => ({
  location: exchange.toString(),
}));

const {
  collection,
  isLoading,
  pagination,
  refetch: fetchData,
  sort,
} = useServerTable<
  ExchangeSavingsEvent,
  ExchangeSavingsRequestPayload
>({
  async fetch(payload) {
    const { assets = [], received = [], ...collection } = await fetchExchangeSavings(payload);
    set(savingsAssets, assets);
    set(savingsReceived, received);
    return collection;
  },
  params: [{ isDefault: true, to: 'request', values: defaultParams }],
  sort: {
    default: {
      direction: 'asc',
    },
  },
  urlState: { mode: 'route' },
});

const receivedTableSort = ref<DataTableSortData<AssetBalance>>({
  column: 'value',
  direction: 'desc' as const,
});

const receivedTableHeaders = computed<DataTableColumn<AssetBalance>[]>(() => [{
  key: 'asset',
  label: t('common.asset'),
  sortable: true,
}, {
  align: 'end',
  key: 'amount',
  label: t('common.amount'),
  sortable: true,
}, {
  align: 'end',
  key: 'value',
  label: t('common.value_in_symbol', {
    symbol: get(currencySymbol),
  }),
  sortable: true,
}]);

const tableHeaders = computed<DataTableColumn<ExchangeSavingsEvent>[]>(() => [{
  key: 'timestamp',
  label: t('common.datetime'),
  sortable: true,
}, {
  key: 'asset',
  label: t('common.asset'),
  sortable: true,
}, {
  align: 'end',
  key: 'amount',
  label: t('common.amount'),
  sortable: true,
}, {
  align: 'end',
  key: 'value',
  label: t('common.value_in_symbol', {
    symbol: get(currencySymbol),
  }),
  sortable: true,
}]);

useRememberTableSorting<AssetBalance>(TableId.BINANCE_RECEIVED_SAVING, receivedTableSort, receivedTableHeaders);
useRememberTableSorting<ExchangeSavingsEvent>(TableId.BINANCE_RECEIVED_SAVING_EVENTS, sort, tableHeaders);

watch(loading, async (isLoading, wasLoading) => {
  if (!isLoading && wasLoading)
    await fetchData();
});

watchImmediate(currencySymbol, async () => {
  await fetchData();
});
</script>

<template>
  <div class="flex flex-col gap-6">
    <RuiCard>
      <template #header>
        {{ t('exchange_balances.received_interest') }}
      </template>

      <RuiDataTable
        v-model:sort="receivedTableSort"
        outlined
        dense
        :cols="receivedTableHeaders"
        :rows="savingsReceived"
        :loading="isLoading"
        row-attr="asset"
      >
        <template #item.asset="{ row }">
          <AssetDetails :asset="row.asset" />
        </template>
        <template #item.amount="{ row }">
          <ValueDisplay :value="row.amount" />
        </template>
        <template #item.value="{ row }">
          <FiatDisplay :value="row.value" />
        </template>
        <template
          v-if="savingsReceived.length > 0"
          #body.append
        >
          <RowAppend
            label-colspan="2"
            :label="t('common.total')"
            class="[&>td]:p-4"
          >
            <FiatDisplay
              v-if="collection.totalValue"
              :value="collection.totalValue"
            />
          </RowAppend>
        </template>
      </RuiDataTable>
    </RuiCard>
    <RuiCard>
      <template #header>
        {{ t('exchange_balances.received_interest_history') }}
      </template>

      <RuiDataTable
        v-model:sort="sort"
        v-model:pagination.external="pagination"
        outlined
        dense
        :cols="tableHeaders"
        :rows="collection.data"
        row-attr="asset"
        :loading="isLoading"
      >
        <template #item.asset="{ row }">
          <AssetDetails :asset="row.asset" />
        </template>
        <template #item.amount="{ row }">
          <ValueDisplay :value="row.amount" />
        </template>
        <template #item.value="{ row }">
          <AssetValueDisplay
            :key="row.timestamp"
            :asset="row.asset"
            :amount="row.amount"
            :timestamp="row.timestamp"
          />
        </template>
        <template #item.timestamp="{ row }">
          <DateDisplay :timestamp="row.timestamp" />
        </template>
      </RuiDataTable>
    </RuiCard>
  </div>
</template>
