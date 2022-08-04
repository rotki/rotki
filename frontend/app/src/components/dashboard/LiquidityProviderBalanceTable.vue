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
        :value="totalInUsd"
        show-currency="symbol"
        fiat-currency="USD"
      />
    </template>
    <data-table
      :headers="tableHeaders"
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
        <liquidity-provider-balance-details
          :span="headers.length"
          :assets="item.assets"
        />
      </template>
      <template #body.append="{ isMobile }">
        <row-append
          label-colspan="1"
          :label="$t('common.total')"
          :right-patch-colspan="tableHeaders.length - 2"
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
import { BigNumber } from '@rotki/common';
import { XswapBalance } from '@rotki/common/lib/defi/xswap';
import { computed, ref, Ref } from '@vue/composition-api';
import { get } from '@vueuse/core';
import { storeToRefs } from 'pinia';
import { DataTableHeader } from 'vuetify';
import DashboardExpandableTable from '@/components/dashboard/DashboardExpandableTable.vue';
import LiquidityProviderBalanceDetails from '@/components/dashboard/LiquidityProviderBalanceDetails.vue';
import VisibleColumnsSelector from '@/components/dashboard/VisibleColumnsSelector.vue';
import NftDetails from '@/components/helper/NftDetails.vue';
import RowAppend from '@/components/helper/RowAppend.vue';
import { setupGeneralSettings } from '@/composables/session';
import { bigNumberSum } from '@/filters';
import i18nFn from '@/i18n';
import { Routes } from '@/router/routes';
import { useUniswap } from '@/store/defi/uniswap';
import { useFrontendSettingsStore } from '@/store/settings';
import { useStatisticsStore } from '@/store/statistics';
import { useTasks } from '@/store/tasks';
import {
  DashboardTablesVisibleColumns,
  DashboardTableType
} from '@/types/frontend-settings';
import { TableColumn } from '@/types/table-column';
import { TaskType } from '@/types/task-type';
import { calculatePercentage } from '@/utils/calculation';
import { getNftBalance } from '@/utils/nft';

const createTableHeaders = (
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

const route = Routes.DEFI_DEPOSITS_LIQUIDITY.route;
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
const { dashboardTablesVisibleColumns } = storeToRefs(
  useFrontendSettingsStore()
);

const tableHeaders = createTableHeaders(
  currencySymbol,
  dashboardTablesVisibleColumns
);

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
</script>
