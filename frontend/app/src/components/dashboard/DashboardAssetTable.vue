<script setup lang="ts">
import type { DataTableColumn, DataTableSortData, TablePaginationData } from '@rotki/ui-library';
import ManualBalanceMissingAssetWarning
  from '@/components/accounts/manual-balances/ManualBalanceMissingAssetWarning.vue';
import AssetBalances from '@/components/AssetBalances.vue';
import DashboardExpandableTable from '@/components/dashboard/DashboardExpandableTable.vue';
import VisibleColumnsSelector from '@/components/dashboard/VisibleColumnsSelector.vue';
import AmountDisplay from '@/components/display/amount/AmountDisplay.vue';
import PercentageDisplay from '@/components/display/PercentageDisplay.vue';
import EvmNativeTokenBreakdown from '@/components/EvmNativeTokenBreakdown.vue';
import AssetDetails from '@/components/helper/AssetDetails.vue';
import RowAppend from '@/components/helper/RowAppend.vue';
import { useAssetInfoRetrieval } from '@/composables/assets/retrieval';
import { useManualBalanceData } from '@/modules/balances/manual/use-manual-balance-data';
import BalanceTopProtocols from '@/modules/balances/protocols/BalanceTopProtocols.vue';
import { usePriceUtils } from '@/modules/prices/use-price-utils';
import { TableId, useRememberTableSorting } from '@/modules/table/use-remember-table-sorting';
import { Routes } from '@/router/routes';
import { useFrontendSettingsStore } from '@/store/settings/frontend';
import { useGeneralSettingsStore } from '@/store/settings/general';
import { useStatisticsStore } from '@/store/statistics';
import { isEvmNativeToken } from '@/types/asset';
import { CURRENCY_USD } from '@/types/currencies';
import { DashboardTableType } from '@/types/settings/frontend-settings';
import { TableColumn } from '@/types/table-column';
import { assetFilterByKeyword } from '@/utils/assets';
import { sortAssetBalances } from '@/utils/balances';
import { aggregateTotal, calculatePercentage } from '@/utils/calculation';
import { type AssetBalance, type AssetBalanceWithPrice, type BigNumber, type Nullable, One } from '@rotki/common';

const props = withDefaults(
  defineProps<{
    title: string;
    balances: AssetBalanceWithPrice[];
    tableType: DashboardTableType;
    loading?: boolean;
  }>(),
  { loading: false },
);

const { t } = useI18n({ useScope: 'global' });

const { balances, tableType, title } = toRefs(props);
const search = ref('');

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
const { totalNetWorthUsd } = storeToRefs(statisticsStore);
const router = useRouter();

function assetFilter(item: Nullable<AssetBalance>) {
  return assetFilterByKeyword(item, get(search), assetName, assetSymbol);
}

function isAssetMissing(item: AssetBalanceWithPrice) {
  return get(missingCustomAssets).includes(item.asset);
}

const totalInUsd = computed(() => aggregateTotal(get(balances), CURRENCY_USD, One));
const total = computed(() => {
  const mainCurrency = get(currencySymbol);
  return get(totalInUsd).multipliedBy(get(useExchangeRate(mainCurrency)) ?? One);
});

function percentageOfTotalNetValue(value: BigNumber) {
  const netWorth = get(totalNetWorthUsd);
  const total = netWorth.lt(0) ? get(totalInUsd) : netWorth;
  return calculatePercentage(value, total);
}

function percentageOfCurrentGroup(value: BigNumber) {
  return calculatePercentage(value, get(totalInUsd));
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

function getAssets(item: AssetBalanceWithPrice): string[] {
  return item.breakdown?.map(entry => entry.asset) ?? [];
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
    label: t('common.protocol'),
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
      label: get(totalNetWorthUsd).gt(0)
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
          :value="percentageOfTotalNetValue(row.usdValue)"
          :asset-padding="0.1"
        />
      </template>
      <template #item.percentageOfTotalCurrentGroup="{ row }">
        <PercentageDisplay
          :value="percentageOfCurrentGroup(row.usdValue)"
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
          label-colspan="3"
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
        <EvmNativeTokenBreakdown
          v-if="isEvmNativeToken(row.asset)"
          show-percentage
          :total="row.usdValue"
          :assets="getAssets(row)"
          :identifier="row.asset"
          :is-liability="tableType === DashboardTableType.LIABILITIES"
          class="bg-white dark:bg-[#1E1E1E] my-2"
        />
        <AssetBalances
          v-else
          hide-total
          v-bind="props"
          :balances="row.breakdown ?? []"
          all-breakdown
          :is-liability="tableType === DashboardTableType.LIABILITIES"
          class="bg-white dark:bg-[#1E1E1E] my-2"
        />
      </template>
      <template #item.expand="{ row }">
        <RuiTableRowExpander
          v-if="row.breakdown || isEvmNativeToken(row.asset)"
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
