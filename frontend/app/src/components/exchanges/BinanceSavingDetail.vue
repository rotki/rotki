<script setup lang="ts">
import { type DataTableHeader } from 'vuetify';
import { useEmptyFilter } from '@/composables/filters';
import { CURRENCY_USD } from '@/types/currencies';
import {
  type ExchangeSavingsCollection,
  type ExchangeSavingsEvent,
  type ExchangeSavingsRequestPayload,
  type SupportedExchange
} from '@/types/exchanges';
import { Section } from '@/types/status';
import { Zero } from '@/utils/bignumbers';

const props = defineProps<{
  exchange: SupportedExchange.BINANCE | SupportedExchange.BINANCEUS;
}>();

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
} = useHistoryPaginationFilter<
  ExchangeSavingsEvent,
  ExchangeSavingsRequestPayload,
  ExchangeSavingsEvent,
  ExchangeSavingsCollection
>(
  exchange,
  true,
  useEmptyFilter,
  fetchExchangeSavings,
  defaultCollectionState,
  {
    defaultSortBy: {
      pageParamsAsc: [true]
    },
    extraParams
  }
);

watch(loading, async (isLoading, wasLoading) => {
  if (!isLoading && wasLoading) {
    await fetchData();
  }
});

onMounted(async () => {
  await fetchData();
});

const { tc } = useI18n();

const { currencySymbol } = storeToRefs(useGeneralSettingsStore());
const tableHeaders = computed<DataTableHeader[]>(() => [
  {
    text: tc('common.datetime'),
    value: 'timestamp'
  },
  {
    text: tc('common.asset'),
    value: 'asset',
    sortable: false
  },
  {
    text: tc('common.amount'),
    value: 'amount',
    align: 'end'
  },
  {
    text: tc('common.value_in_symbol', 0, {
      symbol: get(currencySymbol)
    }),
    value: 'usdValue',
    align: 'end',
    sortable: false
  }
]);

const receivedTableHeaders = computed<DataTableHeader[]>(() => [
  {
    text: tc('common.asset'),
    value: 'asset',
    sortable: false
  },
  {
    text: tc('common.amount'),
    value: 'amount',
    align: 'end'
  },
  {
    text: tc('common.value_in_symbol', 0, {
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
    <v-sheet outlined rounded>
      <card elevation="0">
        <template #title>
          {{ tc('exchange_balances.received_interest') }}
        </template>

        <div class="pt-4 ma-n4">
          <data-table
            :headers="receivedTableHeaders"
            :items="collection.received"
            :loading="isLoading"
          >
            <template #item.asset="{ item }">
              <asset-details opens-details hide-name :asset="item.asset" />
            </template>
            <template #item.amount="{ item }">
              <amount-display :value="item.amount" />
            </template>
            <template #item.usdValue="{ item }">
              <amount-display :value="item.usdValue" />
            </template>
            <template
              v-if="collection.received.length > 0"
              #body.append="{ isMobile }"
            >
              <row-append
                label-colspan="2"
                :label="tc('common.total')"
                :is-mobile="isMobile"
              >
                <amount-display
                  :fiat-currency="CURRENCY_USD"
                  :value="collection.totalUsdValue"
                  show-currency="symbol"
                />
              </row-append>
            </template>
          </data-table>
        </div>
      </card>
    </v-sheet>
    <v-sheet outlined rounded class="mt-6" :elevation="0">
      <card elevation="0">
        <template #title>
          {{ tc('exchange_balances.received_interest_history') }}
        </template>

        <div class="pt-4 ma-n4">
          <collection-handler :collection="collection">
            <template #default="{ data, itemLength }">
              <data-table
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
                  <asset-details opens-details hide-name :asset="item.asset" />
                </template>
                <template #item.amount="{ item }">
                  <amount-display :value="item.amount" />
                </template>
                <template #item.usdValue="{ item }">
                  <amount-display :value="item.usdValue" />
                </template>
                <template #item.timestamp="{ item }">
                  <date-display :timestamp="item.timestamp" />
                </template>
              </data-table>
            </template>
          </collection-handler>
        </div>
      </card>
    </v-sheet>
  </div>
</template>
