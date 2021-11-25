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
        offset-y
      >
        <template #activator="{ on }">
          <menu-tooltip-button
            :tooltip="$t('dashboard_asset_table.select_showed_columns')"
            class-name="ml-4 dashboard-asset-table__column-filter__button"
            :on-menu="on"
          >
            <v-icon>mdi-dots-vertical</v-icon>
          </menu-tooltip-button>
        </template>
        <showed-columns-selector :group="tableType" :group-label="title" />
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
      <template #header.usdValue>
        <div class="text-no-wrap">
          {{
            $t('dashboard_asset_table.headers.value', {
              symbol: currencySymbol
            })
          }}
        </div>
      </template>
      <template #header.usdPrice>
        <div class="text-no-wrap">
          {{
            $t('dashboard_asset_table.headers.price', {
              symbol: currencySymbol
            })
          }}
        </div>
      </template>
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
      <template v-if="balances.length > 0 && search.length < 1" #body.append>
        <tr
          v-if="$vuetify.breakpoint.smAndUp"
          class="dashboard-asset-table__balances__total font-weight-medium"
        >
          <td colspan="3">{{ $t('dashboard_asset_table.total') }}</td>
          <td class="text-end">
            <amount-display
              :fiat-currency="currencySymbol"
              :value="total"
              show-currency="symbol"
            />
          </td>
          <td />
        </tr>
        <tr v-else>
          <td>
            <v-row class="justify-space-between">
              <v-col cols="auto" class="font-weight-medium">
                {{ $t('dashboard_asset_table.total') }}
              </v-col>
              <v-col cols="auto">
                <amount-display
                  :fiat-currency="currencySymbol"
                  :value="total"
                  show-currency="symbol"
                />
              </v-col>
            </v-row>
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
import ShowedColumnsSelector from '@/components/dashboard/ShowedColumnsSelector.vue';
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
import { DashboardTableType } from '@/types/frontend-settings';
import { TableColumn } from '@/types/table-column';
import { getSortItems } from '@/utils/assets';

const tableHeaders = (
  totalNetWorthUsd: Ref<BigNumber>,
  title: string,
  showedColumns: TableColumn[]
) =>
  computed<DataTableHeader[]>(() => {
    const headers: DataTableHeader[] = [
      {
        text: i18n.t('dashboard_asset_table.headers.asset').toString(),
        value: 'asset',
        cellClass: 'asset-info'
      },
      {
        text: i18n.t('dashboard_asset_table.headers.price').toString(),
        value: 'usdPrice',
        align: 'end'
      },
      {
        text: i18n.t('dashboard_asset_table.headers.amount').toString(),
        value: 'amount',
        align: 'end',
        cellClass: 'asset-divider'
      },
      {
        text: i18n.t('dashboard_asset_table.headers.value').toString(),
        value: 'usdValue',
        align: 'end',
        class: 'text-no-wrap'
      }
    ];

    if (showedColumns.includes(TableColumn.PERCENTAGE_OF_TOTAL_NET_VALUE)) {
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

    if (showedColumns.includes(TableColumn.PERCENTAGE_OF_TOTAL_CURRENT_GROUP)) {
      headers.push({
        text: i18n
          .t(
            'dashboard_asset_table.headers.percentage_of_total_current_group',
            {
              group: title
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
  components: { ShowedColumnsSelector, MenuTooltipButton },
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
    const total = computed(() => {
      const mainCurrency = currencySymbol.value;
      return aggregateTotal(
        balances.value,
        mainCurrency,
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

    const totalUsd = computed(() => {
      return balances.value.reduce(
        (sum, balance) => sum.plus(balance.usdValue),
        new BigNumber(0)
      );
    });

    const calculatePercentage = (value: BigNumber, divider: BigNumber) => {
      return value.div(divider).multipliedBy(100).toFixed(2);
    };

    const percentageOfTotalNetValue = (value: BigNumber) => {
      const netWorth = totalNetWorthUsd.value;
      const total = netWorth.lt(0) ? totalUsd.value : netWorth;
      return calculatePercentage(value, total);
    };

    const percentageOfCurrentGroup = (value: BigNumber) => {
      return calculatePercentage(value, total.value);
    };

    const { getAssetInfo } = setupAssetInfoRetrieval();

    const { dashboardTablesShowedColumns } = setupSettings();

    const showedColumns = dashboardTablesShowedColumns.value[tableType.value];

    return {
      search,
      total,
      tableHeaders: tableHeaders(totalNetWorthUsd, title.value, showedColumns),
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
