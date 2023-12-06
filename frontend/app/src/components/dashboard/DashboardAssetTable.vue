<script setup lang="ts">
import {
  type AssetBalance,
  type AssetBalanceWithPrice,
  type BigNumber
} from '@rotki/common';
import { type Ref } from 'vue';
import { type DataTableHeader } from '@/types/vuetify';
import { type Nullable } from '@/types';
import { CURRENCY_USD } from '@/types/currencies';
import { type DashboardTableType } from '@/types/settings/frontend-settings';
import { TableColumn } from '@/types/table-column';
import { isEvmNativeToken } from '@/types/asset';

const props = withDefaults(
  defineProps<{
    title: string;
    balances: AssetBalanceWithPrice[];
    tableType: DashboardTableType;
    loading?: boolean;
  }>(),
  { loading: false }
);

const { t } = useI18n();

const { balances, title, tableType } = toRefs(props);
const search = ref('');

const expanded: Ref<AssetBalanceWithPrice[]> = ref([]);

const { currencySymbol } = storeToRefs(useGeneralSettingsStore());

const { exchangeRate } = useBalancePricesStore();
const totalInUsd = computed(() =>
  aggregateTotal(get(balances), CURRENCY_USD, One)
);
const total = computed(() => {
  const mainCurrency = get(currencySymbol);
  return get(totalInUsd).multipliedBy(get(exchangeRate(mainCurrency)) ?? One);
});

const { assetSymbol, assetName, assetInfo } = useAssetInfoRetrieval();

const assetFilter = (
  _value: Nullable<string>,
  search: Nullable<string>,
  item: Nullable<AssetBalance>
) => {
  if (!search || !item) {
    return true;
  }
  const keyword = search?.toLocaleLowerCase()?.trim() ?? '';
  const name = get(assetName(item.asset))?.toLocaleLowerCase()?.trim();
  const symbol = get(assetSymbol(item.asset))?.toLocaleLowerCase()?.trim();
  return symbol.includes(keyword) || name.includes(keyword);
};

const statisticsStore = useStatisticsStore();
const { totalNetWorthUsd } = storeToRefs(statisticsStore);
const percentageOfTotalNetValue = (value: BigNumber) => {
  const netWorth = get(totalNetWorthUsd) as BigNumber;
  const total = netWorth.lt(0) ? get(totalInUsd) : netWorth;
  return calculatePercentage(value, total);
};

const percentageOfCurrentGroup = (value: BigNumber) =>
  calculatePercentage(value, get(totalInUsd));

const { dashboardTablesVisibleColumns } = storeToRefs(
  useFrontendSettingsStore()
);

const sortItems = getSortItems(asset => get(assetInfo(asset)));

const tableHeaders = computed<DataTableHeader[]>(() => {
  const visibleColumns = get(dashboardTablesVisibleColumns)[get(tableType)];

  const headers: DataTableHeader[] = [
    {
      text: t('common.asset').toString(),
      value: 'asset',
      class: 'text-no-wrap',
      width: '99%'
    },
    {
      text: t('common.price_in_symbol', {
        symbol: get(currencySymbol)
      }).toString(),
      value: 'usdPrice',
      align: 'end',
      class: 'text-no-wrap'
    },
    {
      text: t('common.amount').toString(),
      value: 'amount',
      align: 'end'
    },
    {
      text: t('common.value_in_symbol', {
        symbol: get(currencySymbol)
      }).toString(),
      value: 'usdValue',
      align: 'end',
      class: 'text-no-wrap'
    }
  ];

  if (visibleColumns.includes(TableColumn.PERCENTAGE_OF_TOTAL_NET_VALUE)) {
    headers.push({
      text: get(totalNetWorthUsd).gt(0)
        ? t(
            'dashboard_asset_table.headers.percentage_of_total_net_value'
          ).toString()
        : t('dashboard_asset_table.headers.percentage_total').toString(),
      value: 'percentageOfTotalNetValue',
      align: 'end',
      cellClass: 'asset-percentage',
      class: 'text-no-wrap',
      sortable: false
    });
  }

  if (visibleColumns.includes(TableColumn.PERCENTAGE_OF_TOTAL_CURRENT_GROUP)) {
    headers.push({
      text: t(
        'dashboard_asset_table.headers.percentage_of_total_current_group',
        {
          group: get(title)
        }
      ).toString(),
      value: 'percentageOfTotalCurrentGroup',
      align: 'end',
      cellClass: 'asset-percentage',
      class: 'text-no-wrap',
      sortable: false
    });
  }

  headers.push({
    text: '',
    width: '48px',
    value: 'expand',
    sortable: false
  });

  return headers;
});
</script>

<template>
  <DashboardExpandableTable>
    <template #title>{{ title }}</template>
    <template #details>
      <RuiTextField
        v-model="search"
        variant="outlined"
        dense
        prepend-icon="search-line"
        :label="t('common.actions.search')"
        class="p-0 m-0 mr-4 dashboard-asset-table__search"
        hide-details
        clearable
        @click:clear="search = ''"
      />
      <VMenu
        id="dashboard-asset-table__column-filter"
        transition="slide-y-transition"
        max-width="250px"
        nudge-bottom="20"
        offset-y
        left
      >
        <template #activator="{ on }">
          <MenuTooltipButton
            :tooltip="t('dashboard_asset_table.select_visible_columns')"
            class-name="dashboard-asset-table__column-filter__button"
            :on-menu="on"
          >
            <RuiIcon name="more-2-fill" />
          </MenuTooltipButton>
        </template>
        <VisibleColumnsSelector :group="tableType" :group-label="title" />
      </VMenu>
    </template>
    <template #shortDetails>
      <AmountDisplay
        :fiat-currency="currencySymbol"
        :value="total"
        show-currency="symbol"
      />
    </template>
    <DataTable
      class="dashboard-asset-table__balances"
      :headers="tableHeaders"
      :items="balances"
      :search.sync="search"
      :loading="loading"
      sort-by="usdValue"
      item-key="asset"
      single-expand
      :expanded="expanded"
      :custom-sort="sortItems"
      :custom-filter="assetFilter"
    >
      <template #item.asset="{ item }">
        <AssetDetails
          opens-details
          :asset="item.asset"
          :is-collection-parent="!!item.breakdown"
        />
      </template>
      <template #item.usdPrice="{ item }">
        <AmountDisplay
          v-if="item.usdPrice && item.usdPrice.gte(0)"
          no-scramble
          show-currency="symbol"
          :price-asset="item.asset"
          :price-of-asset="item.usdPrice"
          fiat-currency="USD"
          :value="item.usdPrice"
        />
        <div v-else class="flex justify-end">
          <VSkeletonLoader width="70" type="text" />
        </div>
      </template>
      <template #item.amount="{ item }">
        <AmountDisplay :value="item.amount" />
      </template>
      <template #item.usdValue="{ item }">
        <AmountDisplay
          show-currency="symbol"
          :amount="item.amount"
          :price-asset="item.asset"
          :price-of-asset="item.usdPrice"
          fiat-currency="USD"
          :value="item.usdValue"
        />
      </template>
      <template #item.percentageOfTotalNetValue="{ item }">
        <PercentageDisplay :value="percentageOfTotalNetValue(item.usdValue)" />
      </template>
      <template #item.percentageOfTotalCurrentGroup="{ item }">
        <PercentageDisplay :value="percentageOfCurrentGroup(item.usdValue)" />
      </template>
      <template #no-results>
        <span class="grey--text text--darken-2">
          {{
            t('dashboard_asset_table.no_search_result', {
              search
            })
          }}
        </span>
      </template>
      <template
        v-if="balances.length > 0 && (!search || search.length === 0)"
        #body.append="{ isMobile }"
      >
        <RowAppend
          label-colspan="3"
          :label="t('common.total')"
          :right-patch-colspan="tableHeaders.length - 4"
          :is-mobile="isMobile"
        >
          <AmountDisplay
            :fiat-currency="currencySymbol"
            :value="total"
            show-currency="symbol"
          />
        </RowAppend>
      </template>
      <template #expanded-item="{ item }">
        <TableExpandContainer visible :colspan="tableHeaders.length">
          <EvmNativeTokenBreakdown
            v-if="isEvmNativeToken(item.asset)"
            show-percentage
            :total="item.usdValue"
            :identifier="item.asset"
          />
          <AssetBalances
            v-else
            hide-total
            v-bind="props"
            :balances="item.breakdown ?? []"
          />
        </TableExpandContainer>
      </template>
      <template #item.expand="{ item }">
        <RowExpander
          v-if="item.breakdown || isEvmNativeToken(item.asset)"
          :expanded="expanded.includes(item)"
          @click="expanded = expanded.includes(item) ? [] : [item]"
        />
      </template>
    </DataTable>
  </DashboardExpandableTable>
</template>

<style scoped lang="scss">
.dashboard-asset-table {
  &__search {
    max-width: 450px;
  }
}
</style>
