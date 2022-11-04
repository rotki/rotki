<template>
  <dashboard-expandable-table>
    <template #title>{{ title }}</template>
    <template #details>
      <v-text-field
        v-model="search"
        outlined
        dense
        prepend-inner-icon="mdi-magnify"
        :label="t('common.actions.search')"
        class="pa-0 ma-0 dashboard-asset-table__search"
        single-line
        hide-details
        clearable
        @click:clear="search = ''"
      />
      <v-menu
        id="dashboard-asset-table__column-filter"
        transition="slide-y-transition"
        max-width="250px"
        nudge-bottom="20"
        offset-y
      >
        <template #activator="{ on }">
          <menu-tooltip-button
            :tooltip="tc('dashboard_asset_table.select_visible_columns')"
            class-name="ml-4 dashboard-asset-table__column-filter__button"
            :on-menu="on"
          >
            <v-icon>mdi-dots-vertical</v-icon>
          </menu-tooltip-button>
        </template>
        <visible-columns-selector :group="tableType" :group-label="title" />
      </v-menu>
    </template>
    <template #shortDetails>
      <amount-display
        :fiat-currency="currencySymbol"
        :value="total"
        show-currency="symbol"
      />
    </template>
    <data-table
      class="dashboard-asset-table__balances"
      :headers="tableHeaders"
      :items="balances"
      :search.sync="search"
      :loading="loading"
      sort-by="usdValue"
      :custom-sort="sortItems"
      :custom-filter="assetFilter"
    >
      <template #item.asset="{ item }">
        <asset-details opens-details :asset="item.asset" />
      </template>
      <template #item.usdPrice="{ item }">
        <amount-display
          v-if="item.usdPrice && item.usdPrice.gte(0)"
          show-currency="symbol"
          :price-asset="item.asset"
          :price-of-asset="item.usdPrice"
          fiat-currency="USD"
          :value="item.usdPrice"
        />
        <div v-else class="d-flex justify-end">
          <v-skeleton-loader width="70" type="text" />
        </div>
      </template>
      <template #item.amount="{ item }">
        <amount-display :value="item.amount" />
      </template>
      <template #item.usdValue="{ item }">
        <amount-display
          show-currency="symbol"
          :amount="item.amount"
          :price-asset="item.asset"
          :price-of-asset="item.usdPrice"
          fiat-currency="USD"
          :value="item.usdValue"
        />
      </template>
      <template #item.percentageOfTotalNetValue="{ item }">
        <percentage-display :value="percentageOfTotalNetValue(item.usdValue)" />
      </template>
      <template #item.percentageOfTotalCurrentGroup="{ item }">
        <percentage-display :value="percentageOfCurrentGroup(item.usdValue)" />
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
        v-if="balances.length > 0 && (!search || search.length < 1)"
        #body.append="{ isMobile }"
      >
        <row-append
          label-colspan="3"
          :label="tc('common.total')"
          :right-patch-colspan="tableHeaders.length - 4"
          :is-mobile="isMobile"
        >
          <amount-display
            :fiat-currency="currencySymbol"
            :value="total"
            show-currency="symbol"
          />
        </row-append>
      </template>
    </data-table>
  </dashboard-expandable-table>
</template>

<script setup lang="ts">
import { AssetBalance, AssetBalanceWithPrice, BigNumber } from '@rotki/common';
import { PropType } from 'vue';
import { DataTableHeader } from 'vuetify';
import DashboardExpandableTable from '@/components/dashboard/DashboardExpandableTable.vue';
import VisibleColumnsSelector from '@/components/dashboard/VisibleColumnsSelector.vue';
import MenuTooltipButton from '@/components/helper/MenuTooltipButton.vue';
import RowAppend from '@/components/helper/RowAppend.vue';
import { aggregateTotal } from '@/filters';
import { useAssetInfoRetrieval } from '@/store/assets/retrieval';
import { useBalancePricesStore } from '@/store/balances/prices';
import { useFrontendSettingsStore } from '@/store/settings/frontend';
import { useGeneralSettingsStore } from '@/store/settings/general';
import { useStatisticsStore } from '@/store/statistics';
import { Nullable } from '@/types';
import { CURRENCY_USD } from '@/types/currencies';
import { DashboardTableType } from '@/types/frontend-settings';
import { TableColumn } from '@/types/table-column';
import { getSortItems } from '@/utils/assets';
import { One } from '@/utils/bignumbers';
import { calculatePercentage } from '@/utils/calculation';

const props = defineProps({
  loading: { required: false, type: Boolean, default: false },
  title: { required: true, type: String },
  balances: {
    required: true,
    type: Array as PropType<AssetBalanceWithPrice[]>
  },
  tableType: { required: true, type: String as PropType<DashboardTableType> }
});

const { balances, title, tableType } = toRefs(props);
const search = ref('');

const { currencySymbol } = storeToRefs(useGeneralSettingsStore());

const { t, tc } = useI18n();

const { exchangeRate } = useBalancePricesStore();
const totalInUsd = computed(() => {
  return aggregateTotal(get(balances), CURRENCY_USD, One);
});
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
  return symbol.indexOf(keyword) >= 0 || name.indexOf(keyword) >= 0;
};

const statisticsStore = useStatisticsStore();
const { totalNetWorthUsd } = storeToRefs(statisticsStore);
const percentageOfTotalNetValue = (value: BigNumber) => {
  const netWorth = get(totalNetWorthUsd) as BigNumber;
  const total = netWorth.lt(0) ? get(totalInUsd) : netWorth;
  return calculatePercentage(value, total);
};

const percentageOfCurrentGroup = (value: BigNumber) => {
  return calculatePercentage(value, get(totalInUsd));
};

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
      class: 'text-no-wrap'
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
      align: 'end',
      width: '99%'
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

  return headers;
});
</script>

<style scoped lang="scss">
.dashboard-asset-table {
  &__search {
    max-width: 450px;
  }
}
</style>
