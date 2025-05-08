<script setup lang="ts">
import type { ExchangeSavingsEvent, ExchangeSavingsRequestPayload } from '@/types/exchanges';
import type { AssetBalance } from '@rotki/common';
import type { DataTableColumn, DataTableSortData } from '@rotki/ui-library';
import AmountDisplay from '@/components/display/amount/AmountDisplay.vue';
import DateDisplay from '@/components/display/DateDisplay.vue';
import AssetDetails from '@/components/helper/AssetDetails.vue';
import CollectionHandler from '@/components/helper/CollectionHandler.vue';
import RowAppend from '@/components/helper/RowAppend.vue';
import { usePaginationFilters } from '@/composables/use-pagination-filter';
import { useBinanceSavings } from '@/modules/balances/exchanges/use-binance-savings';
import { TableId, useRememberTableSorting } from '@/modules/table/use-remember-table-sorting';
import { useGeneralSettingsStore } from '@/store/settings/general';
import { useStatusStore } from '@/store/status';
import { CURRENCY_USD } from '@/types/currencies';
import { Section } from '@/types/status';

const props = defineProps<{
  exchange: 'binance' | 'binanceus';
}>();

const { t } = useI18n({ useScope: 'global' });

const { exchange } = toRefs(props);

const savingsAssets = ref<string[]>([]);
const savingsReceived = ref<AssetBalance[]>([]);

const { isLoading: isSectionLoading } = useStatusStore();
const { fetchExchangeSavings } = useBinanceSavings();

const loading = isSectionLoading(Section.EXCHANGE_SAVINGS);
const { currencySymbol } = storeToRefs(useGeneralSettingsStore());

const defaultParams = computed(() => ({
  location: get(exchange).toString(),
}));

const {
  fetchData,
  isLoading,
  pagination,
  sort,
  state: collection,
} = usePaginationFilters<
  ExchangeSavingsEvent,
  ExchangeSavingsRequestPayload
>(async (payload) => {
  const { assets = [], received = [], ...collection } = await fetchExchangeSavings(payload);
  set(savingsAssets, assets);
  set(savingsReceived, received);
  return collection;
}, {
  defaultParams,
  defaultSortBy: {
    direction: 'asc',
  },
  history: 'router',
  locationOverview: exchange,
});

const receivedTableSort = ref<DataTableSortData<AssetBalance>>({
  column: 'usdValue',
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
  key: 'usdValue',
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
  key: 'usdValue',
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

onMounted(async () => {
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
          <AmountDisplay :value="row.amount" />
        </template>
        <template #item.usdValue="{ row }">
          <AmountDisplay
            :value="row.usdValue"
            :fiat-currency="CURRENCY_USD"
          />
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
            <AmountDisplay
              v-if="collection.totalUsdValue"
              :fiat-currency="CURRENCY_USD"
              :value="collection.totalUsdValue"
              show-currency="symbol"
            />
          </RowAppend>
        </template>
      </RuiDataTable>
    </RuiCard>
    <RuiCard>
      <template #header>
        {{ t('exchange_balances.received_interest_history') }}
      </template>

      <CollectionHandler :collection="collection">
        <template #default="{ data }">
          <RuiDataTable
            v-model:sort="sort"
            v-model:pagination.external="pagination"
            outlined
            dense
            :cols="tableHeaders"
            :rows="data"
            row-attr="asset"
            :loading="isLoading"
          >
            <template #item.asset="{ row }">
              <AssetDetails :asset="row.asset" />
            </template>
            <template #item.amount="{ row }">
              <AmountDisplay :value="row.amount" />
            </template>
            <template #item.usdValue="{ row }">
              <AmountDisplay
                :value="row.usdValue"
                :fiat-currency="CURRENCY_USD"
              />
            </template>
            <template #item.timestamp="{ row }">
              <DateDisplay :timestamp="row.timestamp" />
            </template>
          </RuiDataTable>
        </template>
      </CollectionHandler>
    </RuiCard>
  </div>
</template>
