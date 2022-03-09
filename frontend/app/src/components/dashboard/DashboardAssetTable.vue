<template>
  <card outlined-body>
    <template #title>{{ title }}</template>
    <template #details>
      <v-text-field
        v-model="search"
        outlined
        dense
        prepend-inner-icon="mdi-magnify"
        :label="$t('dashboard_asset_table.search')"
        class="pa-0 ma-0 dashboard-asset-table__search"
        single-line
        hide-details
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
            :tooltip="$t('dashboard_asset_table.select_visible_columns')"
            class-name="ml-4 dashboard-asset-table__column-filter__button"
            :on-menu="on"
          >
            <v-icon>mdi-dots-vertical</v-icon>
          </menu-tooltip-button>
        </template>
        <visible-columns-selector :group="tableType" :group-label="title" />
      </v-menu>
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
      <template #item.amount="{ item }">
        <amount-display :value="item.amount" />
      </template>
      <template #item.usdValue="{ item }">
        <amount-display
          show-currency="symbol"
          :fiat-currency="item.asset"
          :amount="item.amount"
          :value="item.usdValue"
        />
      </template>
      <template #item.usdPrice="{ item }">
        <amount-display
          v-if="item.usdPrice && item.usdPrice.gte(0)"
          show-currency="symbol"
          fiat-currency="USD"
          tooltip
          :price-asset="item.asset"
          :value="item.usdPrice"
        />
        <span v-else>-</span>
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
            $t('dashboard_asset_table.no_search_result', {
              search
            })
          }}
        </span>
      </template>
      <template
        v-if="balances.length > 0 && search.length < 1"
        #body.append="{ isMobile }"
      >
        <row-append
          label-colspan="3"
          :label="$t('dashboard_asset_table.total')"
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
  </card>
</template>

<script lang="ts">
import { AssetBalance, AssetBalanceWithPrice, BigNumber } from '@rotki/common';
import {
  computed,
  defineComponent,
  PropType,
  Ref,
  ref,
  toRefs
} from '@vue/composition-api';
import { get } from '@vueuse/core';
import { DataTableHeader } from 'vuetify';
import VisibleColumnsSelector from '@/components/dashboard/VisibleColumnsSelector.vue';
import MenuTooltipButton from '@/components/helper/MenuTooltipButton.vue';
import RowAppend from '@/components/helper/RowAppend.vue';
import { setupExchangeRateGetter } from '@/composables/balances';
import { setupGeneralSettings } from '@/composables/session';
import { setupSettings } from '@/composables/settings';
import { totalNetWorthUsd } from '@/composables/statistics';
import { CURRENCY_USD } from '@/data/currencies';
import { aggregateTotal } from '@/filters';
import i18n from '@/i18n';
import { useAssetInfoRetrieval } from '@/store/assets';
import { Nullable } from '@/types';
import {
  DashboardTablesVisibleColumns,
  DashboardTableType
} from '@/types/frontend-settings';
import { TableColumn } from '@/types/table-column';
import { getSortItems } from '@/utils/assets';

const tableHeaders = (
  totalNetWorthUsd: Ref<BigNumber>,
  currencySymbol: Ref<string>,
  title: Ref<string>,
  dashboardTablesVisibleColumns: Ref<DashboardTablesVisibleColumns>,
  tableType: Ref<DashboardTableType>
) =>
  computed<DataTableHeader[]>(() => {
    const visibleColumns = get(dashboardTablesVisibleColumns)[get(tableType)];

    const headers: DataTableHeader[] = [
      {
        text: i18n.t('dashboard_asset_table.headers.asset').toString(),
        value: 'asset',
        class: 'text-no-wrap'
      },
      {
        text: i18n
          .t('dashboard_asset_table.headers.price', {
            symbol: get(currencySymbol)
          })
          .toString(),
        value: 'usdPrice',
        align: 'end',
        class: 'text-no-wrap'
      },
      {
        text: i18n.t('dashboard_asset_table.headers.amount').toString(),
        value: 'amount',
        align: 'end',
        width: '99%'
      },
      {
        text: i18n
          .t('dashboard_asset_table.headers.value', {
            symbol: get(currencySymbol)
          })
          .toString(),
        value: 'usdValue',
        align: 'end',
        class: 'text-no-wrap'
      }
    ];

    if (visibleColumns.includes(TableColumn.PERCENTAGE_OF_TOTAL_NET_VALUE)) {
      headers.push({
        text: get(totalNetWorthUsd).gt(0)
          ? i18n
              .t('dashboard_asset_table.headers.percentage_of_total_net_value')
              .toString()
          : i18n.t('dashboard_asset_table.headers.percentage_total').toString(),
        value: 'percentageOfTotalNetValue',
        align: 'end',
        cellClass: 'asset-percentage',
        class: 'text-no-wrap',
        sortable: false
      });
    }

    if (
      visibleColumns.includes(TableColumn.PERCENTAGE_OF_TOTAL_CURRENT_GROUP)
    ) {
      headers.push({
        text: i18n
          .t(
            'dashboard_asset_table.headers.percentage_of_total_current_group',
            {
              group: get(title)
            }
          )
          .toString(),
        value: 'percentageOfTotalCurrentGroup',
        align: 'end',
        cellClass: 'asset-percentage',
        class: 'text-no-wrap',
        sortable: false
      });
    }

    return headers;
  });

const DashboardAssetTable = defineComponent({
  name: 'DashboardAssetTable',
  components: { RowAppend, VisibleColumnsSelector, MenuTooltipButton },
  props: {
    loading: { required: false, type: Boolean, default: false },
    title: { required: true, type: String },
    balances: {
      required: true,
      type: Array as PropType<AssetBalanceWithPrice[]>
    },
    tableType: { required: true, type: String as PropType<DashboardTableType> }
  },
  setup(props) {
    const { balances, title, tableType } = toRefs(props);
    const search = ref('');

    const { currencySymbol } = setupGeneralSettings();

    const exchangeRate = setupExchangeRateGetter();
    const totalInUsd = computed(() => {
      return aggregateTotal(get(balances), CURRENCY_USD, new BigNumber(1));
    });
    const total = computed(() => {
      const mainCurrency = get(currencySymbol);
      return get(totalInUsd).multipliedBy(
        exchangeRate(mainCurrency) ?? new BigNumber(1)
      );
    });

    const { getAssetSymbol, getAssetName } = useAssetInfoRetrieval();

    const assetFilter = (
      _value: Nullable<string>,
      search: Nullable<string>,
      item: Nullable<AssetBalance>
    ) => {
      if (!search || !item) {
        return true;
      }
      const keyword = search?.toLocaleLowerCase()?.trim() ?? '';
      const name = getAssetName(item.asset)?.toLocaleLowerCase()?.trim();
      const symbol = getAssetSymbol(item.asset)?.toLocaleLowerCase()?.trim();
      return symbol.indexOf(keyword) >= 0 || name.indexOf(keyword) >= 0;
    };

    const calculatePercentage = (value: BigNumber, divider: BigNumber) => {
      const percentage = divider.isZero()
        ? 0
        : value.div(divider).multipliedBy(100);
      return percentage.toFixed(2);
    };

    const percentageOfTotalNetValue = (value: BigNumber) => {
      const netWorth = get(totalNetWorthUsd);
      const total = netWorth.lt(0) ? get(totalInUsd) : netWorth;
      return calculatePercentage(value, total);
    };

    const percentageOfCurrentGroup = (value: BigNumber) => {
      return calculatePercentage(value, get(totalInUsd));
    };

    const { getAssetInfo } = useAssetInfoRetrieval();

    const { dashboardTablesVisibleColumns } = setupSettings();

    return {
      search,
      total,
      tableHeaders: tableHeaders(
        totalNetWorthUsd,
        currencySymbol,
        title,
        dashboardTablesVisibleColumns,
        tableType
      ),
      currencySymbol,
      sortItems: getSortItems(getAssetInfo),
      assetFilter,
      percentageOfTotalNetValue,
      percentageOfCurrentGroup
    };
  }
});

export default DashboardAssetTable;
</script>

<style scoped lang="scss">
.dashboard-asset-table {
  &__search {
    max-width: 450px;
  }
}
</style>
