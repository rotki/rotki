<script setup lang="ts">
import { CURRENCY_USD } from '@/types/currencies';
import { Section } from '@/types/status';
import type { AssetBalance } from '@rotki/common';
import type { DataTableColumn, DataTableSortData } from '@rotki/ui-library';
import type { ExchangeSavingsEvent, ExchangeSavingsRequestPayload } from '@/types/exchanges';

const props = defineProps<{
  exchange: 'binance' | 'binanceus';
}>();

const { t } = useI18n();

const { exchange } = toRefs(props);

const savingsAssets = ref<string[]>([]);
const savingsReceived = ref<AssetBalance[]>([]);

const { isLoading: isSectionLoading } = useStatusStore();
const { fetchExchangeSavings } = useExchangeBalancesStore();

const loading = isSectionLoading(Section.EXCHANGE_SAVINGS);
const { currencySymbol } = storeToRefs(useGeneralSettingsStore());

const defaultParams = computed(() => ({
  location: get(exchange).toString(),
}));

const {
  isLoading,
  state: collection,
  pagination,
  sort,
  fetchData,
} = usePaginationFilters<
  ExchangeSavingsEvent,
  ExchangeSavingsRequestPayload
>(async (payload) => {
  const { received = [], assets = [], ...collection } = await fetchExchangeSavings(payload);
  set(savingsAssets, assets);
  set(savingsReceived, received);
  return collection;
}, {
  history: 'router',
  locationOverview: exchange,
  defaultSortBy: {
    direction: 'asc',
  },
  defaultParams,
});

const receivedTableSort = ref<DataTableSortData<AssetBalance>>({
  column: 'usdValue',
  direction: 'desc' as const,
});

const receivedTableHeaders = computed<DataTableColumn<AssetBalance>[]>(() => [
  {
    label: t('common.asset'),
    key: 'asset',
    sortable: true,
  },
  {
    label: t('common.amount'),
    key: 'amount',
    align: 'end',
    sortable: true,
  },
  {
    label: t('common.value_in_symbol', {
      symbol: get(currencySymbol),
    }),
    key: 'usdValue',
    align: 'end',
    sortable: true,
  },
]);

const tableHeaders = computed<DataTableColumn<ExchangeSavingsEvent>[]>(() => [
  {
    label: t('common.datetime'),
    key: 'timestamp',
    sortable: true,
  },
  {
    label: t('common.asset'),
    key: 'asset',
    sortable: true,
  },
  {
    label: t('common.amount'),
    key: 'amount',
    align: 'end',
    sortable: true,
  },
  {
    label: t('common.value_in_symbol', {
      symbol: get(currencySymbol),
    }),
    key: 'usdValue',
    align: 'end',
    sortable: true,
  },
]);

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
          <AssetDetails
            opens-details
            hide-name
            :asset="row.asset"
          />
        </template>
        <template #item.amount="{ row }">
          <AmountDisplay :value="row.amount" />
        </template>
        <template #item.usdValue="{ row }">
          <AmountDisplay :value="row.usdValue" />
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
              v-if="collection.totalValue"
              :fiat-currency="CURRENCY_USD"
              :value="collection.totalValue"
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
              <AssetDetails
                opens-details
                hide-name
                :asset="row.asset"
              />
            </template>
            <template #item.amount="{ row }">
              <AmountDisplay :value="row.amount" />
            </template>
            <template #item.usdValue="{ row }">
              <AmountDisplay :value="row.usdValue" />
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
