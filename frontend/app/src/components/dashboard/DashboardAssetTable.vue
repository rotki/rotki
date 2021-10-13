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
      <template #item.percentage="{ item }">
        <percentage-display :value="percentage(item.usdValue)" />
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
import { AssetBalance, AssetBalanceWithPrice } from '@rotki/common';
import {
  computed,
  defineComponent,
  PropType,
  ref,
  toRefs
} from '@vue/composition-api';
import { default as BigNumber } from 'bignumber.js';
import {
  setupAssetInfoRetrieval,
  setupExchangeRateGetter
} from '@/composables/balances';
import { currency, floatingPrecision } from '@/composables/session';
import { totalNetWorthUsd } from '@/composables/statistics';
import { aggregateTotal } from '@/filters';
import i18n from '@/i18n';
import { Nullable } from '@/types';
import { getSortItems } from '@/utils/assets';

const tableHeaders = [
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
    text: i18n.t('dashboard_asset_table.headers.amount'),
    value: 'amount',
    align: 'end',
    cellClass: 'asset-divider'
  },
  {
    text: i18n.t('dashboard_asset_table.headers.value').toString(),
    value: 'usdValue',
    align: 'end',
    class: 'text-no-wrap'
  },
  {
    text: i18n.t('dashboard_asset_table.headers.percentage').toString(),
    value: 'percentage',
    align: 'end',
    cellClass: 'asset-percentage',
    class: 'text-no-wrap',
    sortable: false
  }
];

const DashboardAssetTable = defineComponent({
  name: 'DashboardAssetTable',
  props: {
    loading: { required: false, type: Boolean, default: false },
    title: { required: true, type: String },
    balances: {
      required: true,
      type: Array as PropType<AssetBalanceWithPrice[]>
    }
  },
  setup(props) {
    const { balances } = toRefs(props);
    const search = ref('');

    const currencySymbol = currency;
    const exchangeRate = setupExchangeRateGetter();
    const total = computed(() => {
      const mainCurrency = currencySymbol.value;
      return aggregateTotal(
        balances.value,
        mainCurrency,
        exchangeRate(mainCurrency) ?? new BigNumber(1),
        floatingPrecision.value
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

    const percentage = (value: BigNumber) => {
      return value.div(totalNetWorthUsd.value).multipliedBy(100).toFixed(2);
    };

    const { getAssetInfo } = setupAssetInfoRetrieval();
    return {
      search,
      total,
      tableHeaders,
      currencySymbol,
      floatingPrecision,
      sortItems: getSortItems(getAssetInfo),
      assetFilter,
      percentage
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
