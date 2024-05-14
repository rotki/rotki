<script setup lang="ts">
import { CURRENCY_USD } from '@/types/currencies';
import { Section } from '@/types/status';
import type {
  DataTableColumn,
  DataTableSortData,
} from '@rotki/ui-library-compat';
import type {
  ExchangeSavingsCollection,
  ExchangeSavingsEvent,
  ExchangeSavingsRequestPayload,
} from '@/types/exchanges';

const props = defineProps<{
  exchange: 'binance' | 'binanceus';
}>();

const { t } = useI18n();

const { exchange } = toRefs(props);

const { isLoading: isSectionLoading } = useStatusStore();
const loading = isSectionLoading(Section.EXCHANGE_SAVINGS);

const { fetchExchangeSavings } = useExchangeBalancesStore();

const defaultParams = computed(() => ({
  location: get(exchange).toString(),
}));

function defaultCollectionState(): ExchangeSavingsCollection {
  return {
    found: 0,
    limit: 0,
    data: [],
    total: 0,
    totalUsdValue: Zero,
    assets: [],
    received: [],
  };
}

const {
  isLoading,
  state: collection,
  pagination,
  sort,
  fetchData,
} = usePaginationFilters<
  ExchangeSavingsEvent,
  ExchangeSavingsRequestPayload,
  ExchangeSavingsEvent,
  ExchangeSavingsCollection
>(exchange, true, useEmptyFilter, fetchExchangeSavings, {
  defaultCollection: defaultCollectionState,
  defaultSortBy: {
    ascending: [true],
  },
  defaultParams,
});

watch(loading, async (isLoading, wasLoading) => {
  if (!isLoading && wasLoading)
    await fetchData();
});

onMounted(async () => {
  await fetchData();
});

const { currencySymbol } = storeToRefs(useGeneralSettingsStore());

const receivedTableSort: Ref<DataTableSortData> = ref({
  column: 'usdValue',
  direction: 'desc' as const,
});

const receivedTableHeaders = computed<DataTableColumn[]>(() => [
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

const tableHeaders = computed<DataTableColumn[]>(() => [
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
</script>

<template>
  <div class="flex flex-col gap-6">
    <RuiCard>
      <template #header>
        {{ t('exchange_balances.received_interest') }}
      </template>

      <RuiDataTable
        outlined
        dense
        :cols="receivedTableHeaders"
        :rows="collection.received"
        :loading="isLoading"
        :sort.sync="receivedTableSort"
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
          v-if="collection.received.length > 0"
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
            outlined
            dense
            :cols="tableHeaders"
            :rows="data"
            :sort.sync="sort"
            :pagination.sync="pagination"
            row-attr="asset"
            :pagination-modifiers="{ external: true }"
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
