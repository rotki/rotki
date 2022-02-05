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
        <tr
          v-if="!isMobile"
          class="dashboard-asset-table__balances__total font-weight-medium"
        >
          <td colspan="3">
            {{ $t('dashboard_asset_table.total') }}
          </td>
          <td class="text-end">
            <amount-display
              :fiat-currency="currencySymbol"
              :value="total"
              show-currency="symbol"
            />
          </td>
          <td
            v-if="tableHeaders.length - 4"
            :colspan="tableHeaders.length - 4"
          />
        </tr>
        <tr v-else>
          <td
            class="d-flex align-center justify-space-between font-weight-medium"
          >
            <div>
              {{ $t('dashboard_asset_table.total') }}
            </div>
            <div>
              <amount-display
                :fiat-currency="currencySymbol"
                :value="total"
                show-currency="symbol"
              />
            </div>
          </td>
        </tr>
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
import { DataTableHeader } from 'vuetify';
import VisibleColumnsSelector from '@/components/dashboard/VisibleColumnsSelector.vue';
import MenuTooltipButton from '@/components/helper/MenuTooltipButton.vue';
import {
  setupAssetInfoRetrieval,
  setupExchangeRateGetter
} from '@/composables/balances';
import { currency } from '@/composables/session';
import { setupSettings } from '@/composables/settings';
import { totalNetWorthUsd } from '@/composables/statistics';
import { aggregateTotal } from '@/filters';
import i18n from '@/i18n';
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
    const visibleColumns = dashboardTablesVisibleColumns.value[tableType.value];

    const headers: DataTableHeader[] = [
      {
        text: i18n.t('dashboard_asset_table.headers.asset').toString(),
        value: 'asset',
        cellClass: 'asset-info'
      },
      {
        text: i18n
          .t('dashboard_asset_table.headers.price', {
            symbol: currencySymbol.value
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
        cellClass: 'asset-divider'
      },
      {
        text: i18n
          .t('dashboard_asset_table.headers.value', {
            symbol: currencySymbol.value
          })
          .toString(),
        value: 'usdValue',
        align: 'end',
        class: 'text-no-wrap'
      }
    ];

    if (visibleColumns.includes(TableColumn.PERCENTAGE_OF_TOTAL_NET_VALUE)) {
      headers.push({
        text: totalNetWorthUsd.value.gt(0)
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
              group: title.value
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
  components: { VisibleColumnsSelector, MenuTooltipButton },
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

    const currencySymbol = currency;
    const exchangeRate = setupExchangeRateGetter();
    const totalInUsd = computed(() => {
      return aggregateTotal(balances.value, 'USD', new BigNumber(1));
    });
    const total = computed(() => {
      const mainCurrency = currencySymbol.value;
      return totalInUsd.value.multipliedBy(
        exchangeRate(mainCurrency) ?? new BigNumber(1)
      );
    });

    const { getAssetSymbol, getAssetName } = setupAssetInfoRetrieval();

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
      const netWorth = totalNetWorthUsd.value;
      const total = netWorth.lt(0) ? totalInUsd.value : netWorth;
      return calculatePercentage(value, total);
    };

    const percentageOfCurrentGroup = (value: BigNumber) => {
      return calculatePercentage(value, totalInUsd.value);
    };

    const { getAssetInfo } = setupAssetInfoRetrieval();

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
::v-deep {
  .asset-divider {
    width: 100%;

    @media (min-width: 2000px) {
      width: 50%;
    }
  }

  .asset-info {
    @media (min-width: 2000px) {
      width: 300px;
    }
  }

  .asset-percentage {
    width: 120px;

    @media (min-width: 2000px) {
      width: 200px;
    }
  }
}

.dashboard-asset-table {
  &__search {
    max-width: 450px;
  }

  &__balances {
    &__total {
      &:hover {
        background-color: transparent !important;
      }
    }
  }
}
</style>
