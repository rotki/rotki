<script setup lang="ts">
import { type MaybeRef } from '@vueuse/core';
import { type ComputedRef, type Ref } from 'vue';
import dropRight from 'lodash/dropRight';
import { type DataTableHeader } from 'vuetify';
import isEqual from 'lodash/isEqual';
import {
  type ExchangeSavingsCollection,
  type ExchangeSavingsEvent,
  type ExchangeSavingsRequestPayload,
  type SupportedExchange
} from '@/types/exchanges';
import { Section } from '@/types/status';
import { Zero } from '@/utils/bignumbers';
import { type TablePagination } from '@/types/pagination';
import { defaultOptions } from '@/utils/collection';
import { CURRENCY_USD } from '@/types/currencies';

const props = defineProps<{
  exchange: SupportedExchange.BINANCE | SupportedExchange.BINANCEUS;
}>();

const { exchange } = toRefs(props);

const { isLoading: isSectionLoading } = useStatusStore();
const loading = isSectionLoading(Section.EXCHANGE_SAVINGS);

const { fetchExchangeSavings } = useExchangeBalancesStore();

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
  execute
} = useAsyncState<
  ExchangeSavingsCollection,
  MaybeRef<ExchangeSavingsRequestPayload>[]
>(args => fetchExchangeSavings(args), defaultCollectionState(), {
  immediate: false,
  resetOnExecute: false,
  delay: 0
});

const options: Ref<TablePagination<ExchangeSavingsEvent>> = ref(
  defaultOptions()
);

const pageParams: ComputedRef<ExchangeSavingsRequestPayload> = computed(() => {
  const { itemsPerPage, page, sortBy, sortDesc } = get(options);
  const offset = (page - 1) * itemsPerPage;

  return {
    limit: itemsPerPage,
    offset,
    orderByAttributes: sortBy?.length > 0 ? sortBy : ['timestamp'],
    location: get(exchange),
    ascending:
      sortDesc && sortDesc.length > 1
        ? dropRight(sortDesc).map(bool => !bool)
        : [true]
  };
});

watch(pageParams, async (params, op) => {
  if (isEqual(params, op)) {
    return;
  }
  await fetchData();
});

const fetchData = async (): Promise<void> => {
  await execute(0, pageParams);
};

const userAction: Ref<boolean> = ref(false);

const setOptions = (newOptions: TablePagination<ExchangeSavingsEvent>) => {
  set(userAction, true);
  set(options, newOptions);
};

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
