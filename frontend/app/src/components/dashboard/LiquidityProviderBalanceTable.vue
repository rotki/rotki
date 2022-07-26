<template>
  <dashboard-expandable-table v-if="balances.length > 0">
    <template #title>
      {{ $t('dashboard.liquidity_provider.title') }}
      <v-btn :to="route" icon class="ml-2">
        <v-icon>mdi-chevron-right</v-icon>
      </v-btn>
    </template>
    <template #details>
      <v-menu
        id="nft_balance_table__column-filter"
        transition="slide-y-transition"
        max-width="250px"
        offset-y
      >
        <template #activator="{ on }">
          <menu-tooltip-button
            :tooltip="$t('dashboard_asset_table.select_visible_columns')"
            class-name="ml-4 nft_balance_table__column-filter__button"
            :on-menu="on"
          >
            <v-icon>mdi-dots-vertical</v-icon>
          </menu-tooltip-button>
        </template>
        <visible-columns-selector
          group="LIQUIDITY_PROVIDER"
          :group-label="$t('dashboard.liquidity_provider.short').toString()"
        />
      </v-menu>
    </template>
    <template #shortDetails>
      <amount-display
        :value="total"
        show-currency="symbol"
        fiat-currency="USD"
      />
    </template>
    <data-table
      :headers="mainHeaders"
      :items="balances"
      item-key="nftId"
      sort-by="userBalance.usdValue"
      :loading="loading"
      show-expand
      :expanded="expanded"
    >
      <template #item.name="{ item }">
        <nft-details :identifier="item.nftId" />
      </template>
      <template #item.usdValue="{ item }">
        <amount-display :value="item.usdValue" fiat-currency="USD" />
      </template>
      <template #item.percentageOfTotalNetValue="{ item }">
        <percentage-display :value="percentageOfTotalNetValue(item.usdValue)" />
      </template>
      <template #item.percentageOfTotalCurrentGroup="{ item }">
        <percentage-display :value="percentageOfCurrentGroup(item.usdValue)" />
      </template>
      <template #expanded-item="{ headers, item }">
        <table-expand-container
          visible
          :colspan="headers.length"
          :padded="false"
        >
          <data-table
            v-if="premium"
            hide-default-footer
            :headers="secondaryHeaders"
            :items="transformAssets(item.assets)"
            item-key="asset"
            sort-by="usdValue"
          >
            <template #item.asset="{ item: childItem }">
              <asset-details opens-details :asset="childItem.asset" />
            </template>
            <template #item.usdPrice="{ item: childItem }">
              <amount-display
                v-if="childItem.usdPrice && childItem.usdPrice.gte(0)"
                show-currency="symbol"
                fiat-currency="USD"
                tooltip
                :price-asset="childItem.asset"
                :value="childItem.usdPrice"
              />
              <span v-else>-</span>
            </template>
            <template #item.amount="{ item: childItem }">
              <amount-display :value="childItem.amount" />
            </template>
            <template #item.usdValue="{ item: childItem }">
              <amount-display
                show-currency="symbol"
                :fiat-currency="childItem.asset"
                :amount="childItem.amount"
                :value="childItem.usdValue"
              />
            </template>
          </data-table>
          <div v-else class="d-flex align-center">
            <v-avatar rounded :color="dark ? 'white' : 'grey lighten-3'">
              <v-icon>mdi-lock</v-icon>
            </v-avatar>
            <div class="ml-4">
              <i18n tag="div" path="uniswap.assets_non_premium">
                <base-external-link
                  :text="$t('uniswap.premium')"
                  :href="$interop.premiumURL"
                />
              </i18n>
            </div>
          </div>
        </table-expand-container>
      </template>
      <template #body.append="{ isMobile }">
        <row-append
          label-colspan="1"
          :label="$t('common.total')"
          :right-patch-colspan="mainHeaders.length - 2"
          :is-mobile="isMobile"
        >
          <amount-display
            :value="totalInUsd"
            show-currency="symbol"
            fiat-currency="USD"
          />
        </row-append>
      </template>
    </data-table>
  </dashboard-expandable-table>
</template>
<script setup lang="ts">
import { AssetBalanceWithPrice, BigNumber } from '@rotki/common';
import { XswapAsset, XswapBalance } from '@rotki/common/lib/defi/xswap';
import { computed, ref, Ref } from '@vue/composition-api';
import { get } from '@vueuse/core';
import { storeToRefs } from 'pinia';
import { DataTableHeader } from 'vuetify';
import BaseExternalLink from '@/components/base/BaseExternalLink.vue';
import DashboardExpandableTable from '@/components/dashboard/DashboardExpandableTable.vue';
import VisibleColumnsSelector from '@/components/dashboard/VisibleColumnsSelector.vue';

import NftDetails from '@/components/helper/NftDetails.vue';
import RowAppend from '@/components/helper/RowAppend.vue';
import { usePrices } from '@/composables/balances';
import { useTheme } from '@/composables/common';
import { getPremium, setupGeneralSettings } from '@/composables/session';
import { setupSettings } from '@/composables/settings';
import { bigNumberSum } from '@/filters';
import i18nFn from '@/i18n';
import { Routes } from '@/router/routes';
import { useUniswap } from '@/store/defi/uniswap';
import { useStatisticsStore } from '@/store/statistics';
import { useTasks } from '@/store/tasks';
import {
  DashboardTablesVisibleColumns,
  DashboardTableType
} from '@/types/frontend-settings';
import { TableColumn } from '@/types/table-column';
import { TaskType } from '@/types/task-type';
import { Zero } from '@/utils/bignumbers';
import { calculatePercentage } from '@/utils/calculation';
import { getNftBalance } from '@/utils/nft';

const createMainHeaders = (
  currency: Ref<string>,
  dashboardTablesVisibleColumns: Ref<DashboardTablesVisibleColumns>
) => {
  return computed<DataTableHeader[]>(() => {
    const visibleColumns = get(dashboardTablesVisibleColumns)[
      DashboardTableType.LIQUIDITY_PROVIDER
    ];

    const headers: DataTableHeader[] = [
      {
        text: i18nFn.t('common.name').toString(),
        value: 'name',
        cellClass: 'text-no-wrap'
      },
      {
        text: i18nFn
          .t('common.value_in_symbol', {
            symbol: get(currency)
          })
          .toString(),
        value: 'usdValue',
        align: 'end',
        class: 'text-no-wrap'
      }
    ];

    if (visibleColumns.includes(TableColumn.PERCENTAGE_OF_TOTAL_NET_VALUE)) {
      headers.push({
        text: i18nFn
          .t('dashboard_asset_table.headers.percentage_of_total_net_value')
          .toString(),
        value: 'percentageOfTotalNetValue',
        align: 'end',
        class: 'text-no-wrap',
        sortable: false
      });
    }

    if (
      visibleColumns.includes(TableColumn.PERCENTAGE_OF_TOTAL_CURRENT_GROUP)
    ) {
      headers.push({
        text: i18nFn
          .t(
            'dashboard_asset_table.headers.percentage_of_total_current_group',
            {
              group: i18nFn.t('dashboard.liquidity_provider.short').toString()
            }
          )
          .toString(),
        value: 'percentageOfTotalCurrentGroup',
        align: 'end',
        class: 'text-no-wrap',
        sortable: false
      });
    }

    headers.push({ text: '', value: 'data-table-expand', sortable: false });

    return headers;
  });
};

const createSecondaryHeaders = (currency: Ref<string>) => {
  return computed<DataTableHeader[]>(() => {
    return [
      {
        text: i18nFn.t('common.asset').toString(),
        value: 'asset',
        cellClass: 'text-no-wrap',
        sortable: false
      },
      {
        text: i18nFn
          .t('common.price', {
            symbol: get(currency)
          })
          .toString(),
        value: 'usdPrice',
        align: 'end',
        class: 'text-no-wrap',
        sortable: false
      },
      {
        text: i18nFn.t('common.amount').toString(),
        value: 'amount',
        align: 'end',
        sortable: false
      },
      {
        text: i18nFn
          .t('common.value_in_symbol', {
            symbol: get(currency)
          })
          .toString(),
        value: 'usdValue',
        align: 'end',
        class: 'text-no-wrap',
        sortable: false
      }
    ];
  });
};

const route = Routes.DEFI_DEPOSITS_LIQUIDITY_UNISWAP_V3.route;
const expanded = ref<XswapBalance[]>([]);

const { uniswapV3Balances } = useUniswap();
const balances = computed(() => {
  return get(uniswapV3Balances([])).map(item => ({
    ...item,
    usdValue: item.userBalance.usdValue,
    name: item.nftId ? getNftBalance(item.nftId)?.name ?? item.nftId : ''
  }));
});

const { currencySymbol } = setupGeneralSettings();
const { dashboardTablesVisibleColumns } = setupSettings();

const mainHeaders = createMainHeaders(
  currencySymbol,
  dashboardTablesVisibleColumns
);
const secondaryHeaders = createSecondaryHeaders(currencySymbol);

const totalInUsd = computed<BigNumber>(() =>
  bigNumberSum(get(balances).map(item => item.usdValue))
);

const { isTaskRunning } = useTasks();
const loading = isTaskRunning(TaskType.DEFI_UNISWAP_V3_BALANCES);

const statistics = useStatisticsStore();
const { totalNetWorthUsd } = storeToRefs(statistics);

const percentageOfTotalNetValue = (value: BigNumber) => {
  const netWorth = get(totalNetWorthUsd) as BigNumber;
  const total = netWorth.lt(0) ? get(totalInUsd) : netWorth;
  return calculatePercentage(value, total);
};

const percentageOfCurrentGroup = (value: BigNumber) => {
  return calculatePercentage(value, get(totalInUsd));
};

const { prices } = usePrices();

const transformAssets = (assets: XswapAsset[]): AssetBalanceWithPrice[] => {
  return assets.map(item => {
    return {
      asset: item.asset,
      usdPrice: get(prices)[item.asset] ?? Zero,
      amount: item.userBalance.amount,
      usdValue: item.userBalance.usdValue
    };
  });
};

const { dark } = useTheme();
const premium = getPremium();
</script>
