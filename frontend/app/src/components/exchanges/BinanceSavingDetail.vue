<script setup lang="ts">
import { type DataTableHeader } from '@/types/vuetify';
import { CURRENCY_USD } from '@/types/currencies';
import {
  type ExchangeSavingsCollection,
  type ExchangeSavingsEvent,
  type ExchangeSavingsRequestPayload,
  type SupportedExchange
} from '@/types/exchanges';
import { Section } from '@/types/status';

const props = defineProps<{
  exchange: SupportedExchange.BINANCE | SupportedExchange.BINANCEUS;
}>();

const { t } = useI18n();

const { exchange } = toRefs(props);

const { isLoading: isSectionLoading } = useStatusStore();
const loading = isSectionLoading(Section.EXCHANGE_SAVINGS);

const { fetchExchangeSavings } = useExchangeBalancesStore();

const extraParams = computed(() => ({
  location: get(exchange).toString()
}));

const defaultCollectionState = (): ExchangeSavingsCollection => ({
  found: 0,
  limit: 0,
  data: [],
  total: 0,
  totalUsdValue: Zero,
  assets: [],
  received: []
});

const {
  isLoading,
  state: collection,
  options,
  fetchData,
  setOptions
} = usePaginationFilters<
  ExchangeSavingsEvent,
  ExchangeSavingsRequestPayload,
  ExchangeSavingsEvent,
  ExchangeSavingsCollection
>(exchange, true, useEmptyFilter, fetchExchangeSavings, {
  defaultCollection: defaultCollectionState,
  defaultSortBy: {
    ascending: [true]
  },
  extraParams
});

watch(loading, async (isLoading, wasLoading) => {
  if (!isLoading && wasLoading) {
    await fetchData();
  }
});

onMounted(async () => {
  await fetchData();
});

const { currencySymbol } = storeToRefs(useGeneralSettingsStore());
const tableHeaders = computed<DataTableHeader[]>(() => [
  {
    text: t('common.datetime'),
    value: 'timestamp'
  },
  {
    text: t('common.asset'),
    value: 'asset',
    sortable: false
  },
  {
    text: t('common.amount'),
    value: 'amount',
    align: 'end'
  },
  {
    text: t('common.value_in_symbol', {
      symbol: get(currencySymbol)
    }),
    value: 'usdValue',
    align: 'end',
    sortable: false
  }
]);

const receivedTableHeaders = computed<DataTableHeader[]>(() => [
  {
    text: t('common.asset'),
    value: 'asset',
    sortable: false
  },
  {
    text: t('common.amount'),
    value: 'amount',
    align: 'end'
  },
  {
    text: t('common.value_in_symbol', {
      symbol: get(currencySymbol)
    }),
    value: 'usdValue',
    align: 'end',
    sortable: false
  }
]);
</script>

<template>
  <div>
    <VSheet outlined rounded>
      <Card elevation="0">
        <template #title>
          {{ t('exchange_balances.received_interest') }}
        </template>

        <div class="pt-4 ma-n4">
          <DataTable
            :headers="receivedTableHeaders"
            :items="collection.received"
            :loading="isLoading"
          >
            <template #item.asset="{ item }">
              <AssetDetails opens-details hide-name :asset="item.asset" />
            </template>
            <template #item.amount="{ item }">
              <AmountDisplay :value="item.amount" />
            </template>
            <template #item.usdValue="{ item }">
              <AmountDisplay :value="item.usdValue" />
            </template>
            <template
              v-if="collection.received.length > 0"
              #body.append="{ isMobile }"
            >
              <RowAppend
                label-colspan="2"
                :label="t('common.total')"
                :is-mobile="isMobile"
              >
                <AmountDisplay
                  :fiat-currency="CURRENCY_USD"
                  :value="collection.totalUsdValue"
                  show-currency="symbol"
                />
              </RowAppend>
            </template>
          </DataTable>
        </div>
      </Card>
    </VSheet>
    <VSheet outlined rounded class="mt-6" :elevation="0">
      <Card elevation="0">
        <template #title>
          {{ t('exchange_balances.received_interest_history') }}
        </template>

        <div class="pt-4 ma-n4">
          <CollectionHandler :collection="collection">
            <template #default="{ data, itemLength }">
              <DataTable
                :headers="tableHeaders"
                :items="data"
                :loading="isLoading"
                :options="options"
                :server-items-length="itemLength"
                multi-sort
                :must-sort="false"
                @update:options="setOptions($event)"
              >
                <template #item.asset="{ item }">
                  <AssetDetails opens-details hide-name :asset="item.asset" />
                </template>
                <template #item.amount="{ item }">
                  <AmountDisplay :value="item.amount" />
                </template>
                <template #item.usdValue="{ item }">
                  <AmountDisplay :value="item.usdValue" />
                </template>
                <template #item.timestamp="{ item }">
                  <DateDisplay :timestamp="item.timestamp" />
                </template>
              </DataTable>
            </template>
          </CollectionHandler>
        </div>
      </Card>
    </VSheet>
  </div>
</template>
