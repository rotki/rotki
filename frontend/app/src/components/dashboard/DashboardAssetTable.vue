<script setup lang="ts">
import type { DataTableColumn, DataTableSortData, TablePaginationData } from '@rotki/ui-library';
import { type AssetBalance, type AssetBalanceWithPrice, type BigNumber, type Nullable, Zero } from '@rotki/common';
import ManualBalanceMissingAssetWarning
  from '@/components/accounts/manual-balances/ManualBalanceMissingAssetWarning.vue';
import DashboardExpandableTable from '@/components/dashboard/DashboardExpandableTable.vue';
import VisibleColumnsSelector from '@/components/dashboard/VisibleColumnsSelector.vue';
import AmountDisplay from '@/components/display/amount/AmountDisplay.vue';
import PercentageDisplay from '@/components/display/PercentageDisplay.vue';
import AssetDetails from '@/components/helper/AssetDetails.vue';
import RowAppend from '@/components/helper/RowAppend.vue';
import { useAssetInfoRetrieval } from '@/composables/assets/retrieval';
import { useManualBalanceData } from '@/modules/balances/manual/use-manual-balance-data';
import BalanceTopProtocols from '@/modules/balances/protocols/BalanceTopProtocols.vue';
import AssetRowDetails from '@/modules/balances/protocols/components/AssetRowDetails.vue';
import { usePriceUtils } from '@/modules/prices/use-price-utils';
import { TableId, useRememberTableSorting } from '@/modules/table/use-remember-table-sorting';
import { Routes } from '@/router/routes';
import { useFrontendSettingsStore } from '@/store/settings/frontend';
import { useGeneralSettingsStore } from '@/store/settings/general';
import { useStatisticsStore } from '@/store/statistics';
import { isEvmNativeToken } from '@/types/asset';
import { DashboardTableType } from '@/types/settings/frontend-settings';
import { TableColumn } from '@/types/table-column';
import { assetFilterByKeyword } from '@/utils/assets';
import { sortAssetBalances } from '@/utils/balances';
import { aggregateTotal, calculatePercentage } from '@/utils/calculation';

const props = withDefaults(defineProps<{
  title: string;
  balances: AssetBalanceWithPrice[];
  tableType: DashboardTableType;
  loading?: boolean;
}>(), { loading: false });

const { t } = useI18n({ useScope: 'global' });

const { balances, tableType, title } = toRefs(props);
const search = ref('');
const debouncedSearch = debouncedRef(search, 200);

const expanded = ref<AssetBalanceWithPrice[]>([]);

const sort = ref<DataTableSortData<AssetBalanceWithPrice>>({
  column: 'usdValue',
  direction: 'desc' as const,
});

const pagination = ref({
  itemsPerPage: 10,
  page: 1,
});

const { currencySymbol } = storeToRefs(useGeneralSettingsStore());
const { useExchangeRate } = usePriceUtils();
const { assetInfo, assetName, assetSymbol } = useAssetInfoRetrieval();
const { dashboardTablesVisibleColumns } = storeToRefs(useFrontendSettingsStore());
const { missingCustomAssets } = useManualBalanceData();
const statisticsStore = useStatisticsStore();
const { totalNetWorth } = storeToRefs(statisticsStore);
const router = useRouter();

function assetFilter(item: Nullable<AssetBalance>) {
  return assetFilterByKeyword(item, get(debouncedSearch), assetName, assetSymbol);
}

function isAssetMissing(item: AssetBalanceWithPrice) {
  return get(missingCustomAssets).includes(item.asset);
}

const total = computed<BigNumber>(() => {
  const currency = get(currencySymbol);
  const rate = get(useExchangeRate(currency)) ?? Zero;
  return aggregateTotal(get(balances), currency, rate);
});

function percentageOfTotalNetValue({ amount, asset, usdValue }: AssetBalanceWithPrice) {
  const currency = get(currencySymbol);
  const netWorth = get(totalNetWorth);
  const rate = get(useExchangeRate(currency)) ?? Zero;
  const value = currency === asset ? amount : usdValue.multipliedBy(rate);
  const totalWorth = netWorth.lt(0) ? get(total) : netWorth;
  return calculatePercentage(value, totalWorth);
}

function percentageOfCurrentGroup({ amount, asset, usdValue }: AssetBalanceWithPrice) {
  const currency = get(currencySymbol);
  const rate = get(useExchangeRate(currency)) ?? Zero;
  const value = currency === asset ? amount : usdValue.multipliedBy(rate);
  return calculatePercentage(value, get(total));
}

function setPage(page: number) {
  set(pagination, {
    ...get(pagination),
    page,
  });
}

function setTablePagination(event: TablePaginationData | undefined) {
  if (!isDefined(event))
    return;

  const { limit, page } = event;
  set(pagination, {
    itemsPerPage: limit,
    page,
  });
}

const sorted = computed<AssetBalanceWithPrice[]>(() => {
  const filteredBalances = get(balances).filter(assetFilter);
  return sortAssetBalances(filteredBalances, get(sort), assetInfo);
});

const tableHeaders = computed<DataTableColumn<AssetBalanceWithPrice>[]>(() => {
  const visibleColumns = get(dashboardTablesVisibleColumns)[get(tableType)];

  const headers: DataTableColumn<AssetBalanceWithPrice>[] = [{
    cellClass: 'py-0',
    class: 'text-no-wrap w-full',
    key: 'asset',
    label: t('common.asset'),
    sortable: true,
  }, {
    align: 'end',
    cellClass: 'py-0',
    class: 'text-no-wrap w-full',
    key: 'protocol',
    label: t('common.location'),
    sortable: true,
  }, {
    align: 'end',
    cellClass: 'py-0',
    class: 'text-no-wrap',
    key: 'usdPrice',
    label: t('common.price_in_symbol', {
      symbol: get(currencySymbol),
    }),
    sortable: true,
  }, {
    align: 'end',
    cellClass: 'py-0',
    key: 'amount',
    label: t('common.amount'),
    sortable: true,
  }, {
    align: 'end',
    cellClass: 'py-0',
    class: 'text-no-wrap',
    key: 'usdValue',
    label: t('common.value_in_symbol', {
      symbol: get(currencySymbol),
    }),
    sortable: true,
  }];

  if (visibleColumns.includes(TableColumn.PERCENTAGE_OF_TOTAL_NET_VALUE)) {
    headers.push({
      align: 'end',
      cellClass: 'py-0',
      class: 'text-no-wrap',
      key: 'percentageOfTotalNetValue',
      label: get(totalNetWorth).gt(0)
        ? t('dashboard_asset_table.headers.percentage_of_total_net_value')
        : t('dashboard_asset_table.headers.percentage_total'),
    });
  }

  if (visibleColumns.includes(TableColumn.PERCENTAGE_OF_TOTAL_CURRENT_GROUP)) {
    headers.push({
      align: 'end',
      cellClass: 'py-0',
      class: 'text-no-wrap',
      key: 'percentageOfTotalCurrentGroup',
      label: t('dashboard_asset_table.headers.percentage_of_total_current_group', {
        group: get(title),
      }),
    });
  }

  return headers;
});

useRememberTableSorting<AssetBalanceWithPrice>(TableId.DASHBOARD_ASSET, sort, tableHeaders);

function redirectToManualBalance(item: AssetBalanceWithPrice) {
  const tableType = props.tableType;
  if ([DashboardTableType.ASSETS, DashboardTableType.LIABILITIES].includes(tableType)) {
    router.push({
      path: `${Routes.BALANCES_MANUAL}/${tableType.toLowerCase()}`,
      query: {
        asset: item.asset,
      },
    });
  }
}

function isRowExpandable(row: AssetBalanceWithPrice): boolean {
  const hasBreakdown = Boolean(row.breakdown);
  const isNativeToken = isEvmNativeToken(row.asset);
  const hasMultipleProtocols = (row.perProtocol?.length ?? 0) > 1;

  return hasBreakdown || isNativeToken || hasMultipleProtocols;
}

watch(search, () => setPage(1));
</script>

<template>
  <DashboardExpandableTable>
    <template #title>
      {{ title }}
    </template>
    <template #details>
      <RuiTextField
        v-model="search"
        variant="outlined"
        color="primary"
        dense
        prepend-icon="lu-search"
        :label="t('common.actions.search')"
        :class="$style['dashboard-asset-table__search']"
        hide-details
        clearable
        @click:clear="search = ''"
      />

      <VisibleColumnsSelector
        :group="tableType"
        :group-label="title"
      />
    </template>
    <template #shortDetails>
      <AmountDisplay
        :fiat-currency="currencySymbol"
        :value="total"
        show-currency="symbol"
        class="text-h6 font-bold"
      />
    </template>
    <RuiDataTable
      v-model:sort.external="sort"
      data-cy="dashboard-asset-table__balances"
      :cols="tableHeaders"
      :rows="sorted"
      :loading="loading"
      :empty="{ description: t('data_table.no_data') }"
      :expanded="expanded"
      :pagination="{
        page: pagination.page,
        limit: pagination.itemsPerPage,
        total: sorted.length,
      }"
      row-attr="asset"
      sticky-header
      single-expand
      outlined
      dense
      @update:pagination="setTablePagination($event)"
    >
      <template #item.asset="{ row }">
        <ManualBalanceMissingAssetWarning
          v-if="isAssetMissing(row)"
          @click="redirectToManualBalance(row)"
        />

        <AssetDetails
          v-else
          :asset="row.asset"
          :is-collection-parent="!!row.breakdown"
        />
      </template>
      <template #item.protocol="{ row }">
        <BalanceTopProtocols
          v-if="row.perProtocol"
          :protocols="row.perProtocol"
          :loading="!row.usdPrice || row.usdPrice.lt(0)"
          :asset="row.asset"
        />
      </template>
      <template #item.usdPrice="{ row }">
        <template v-if="isAssetMissing(row)">
          -
        </template>
        <AmountDisplay
          v-else
          :loading="!row.usdPrice || row.usdPrice.lt(0)"
          is-asset-price
          show-currency="symbol"
          :price-asset="row.asset"
          :price-of-asset="row.usdPrice"
          fiat-currency="USD"
          :value="row.usdPrice"
        />
      </template>
      <template #item.amount="{ row }">
        <AmountDisplay :value="row.amount" />
      </template>
      <template #item.usdValue="{ row }">
        <AmountDisplay
          show-currency="symbol"
          :amount="row.amount"
          :price-asset="row.asset"
          :price-of-asset="row.usdPrice"
          fiat-currency="USD"
          :value="row.usdValue"
        />
      </template>
      <template #item.percentageOfTotalNetValue="{ row }">
        <PercentageDisplay
          :value="percentageOfTotalNetValue(row)"
          :asset-padding="0.1"
        />
      </template>
      <template #item.percentageOfTotalCurrentGroup="{ row }">
        <PercentageDisplay
          :value="percentageOfCurrentGroup(row)"
          :asset-padding="0.1"
        />
      </template>
      <template
        v-if="search.length > 0"
        #no-data
      >
        <span class="text-rui-text-secondary">
          {{ t('dashboard_asset_table.no_search_result', { search }) }}
        </span>
      </template>
      <template
        v-if="balances.length > 0 && (!search || search.length === 0)"
        #body.append
      >
        <RowAppend
          label-colspan="4"
          :label="t('common.total')"
          :right-patch-colspan="tableHeaders.length - 4"
          :class-name="$style['dashboard-asset-table__body-append']"
        >
          <AmountDisplay
            :fiat-currency="currencySymbol"
            :value="total"
            show-currency="symbol"
          />
        </RowAppend>
      </template>
      <template #expanded-item="{ row }">
        <AssetRowDetails
          :row="row"
          :is-liability="tableType === DashboardTableType.LIABILITIES"
          :loading="loading"
        />
      </template>
      <template #item.expand="{ row }">
        <RuiTableRowExpander
          v-if="isRowExpandable(row)"
          :expanded="expanded.includes(row)"
          @click="expanded = expanded.includes(row) ? [] : [row]"
        />
      </template>
    </RuiDataTable>
  </DashboardExpandableTable>
</template>

<style module lang="scss">
.dashboard-asset-table {
  &__search {
    @apply max-w-[28rem] w-full;
  }

  &__body-append {
    @apply text-sm;

    td {
      @apply p-4;
    }
  }
}
</style>
