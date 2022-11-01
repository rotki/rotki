<template>
  <dashboard-expandable-table>
    <template #title>
      <refresh-button
        :loading="loading"
        :tooltip="tc('nft_balance_table.refresh')"
        @refresh="refresh"
      />
      {{ tc('nft_balance_table.title') }}
      <v-btn :to="nonFungibleRoute" icon class="ml-2">
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
            :tooltip="tc('dashboard_asset_table.select_visible_columns')"
            class-name="ml-4 nft_balance_table__column-filter__button"
            :on-menu="on"
          >
            <v-icon>mdi-dots-vertical</v-icon>
          </menu-tooltip-button>
        </template>
        <visible-columns-selector :group="group" />
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
      :headers="tableHeaders"
      :items="filteredBalances"
      sort-by="usdPrice"
      :loading="loading"
    >
      <template #item.name="{ item }">
        <nft-details :identifier="item.id" />
      </template>
      <template #item.priceInAsset="{ item }">
        <amount-display
          v-if="item.priceAsset !== currencySymbol"
          :value="item.priceInAsset"
          :asset="item.priceAsset"
        />
        <span v-else>-</span>
      </template>
      <template #item.usdPrice="{ item }">
        <amount-display
          :value="item.usdPrice"
          show-currency="symbol"
          fiat-currency="USD"
        />
      </template>
      <template #item.percentageOfTotalNetValue="{ item }">
        <percentage-display :value="percentageOfTotalNetValue(item.usdPrice)" />
      </template>
      <template #item.percentageOfTotalCurrentGroup="{ item }">
        <percentage-display :value="percentageOfCurrentGroup(item.usdPrice)" />
      </template>
      <template #body.append="{ isMobile }">
        <row-append
          label-colspan="2"
          :label="tc('common.total')"
          :right-patch-colspan="tableHeaders.length - 3"
          :is-mobile="isMobile"
        >
          <amount-display
            :value="total"
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
import { DataTableHeader } from 'vuetify';
import DashboardExpandableTable from '@/components/dashboard/DashboardExpandableTable.vue';
import VisibleColumnsSelector from '@/components/dashboard/VisibleColumnsSelector.vue';
import NftDetails from '@/components/helper/NftDetails.vue';
import RefreshButton from '@/components/helper/RefreshButton.vue';
import RowAppend from '@/components/helper/RowAppend.vue';
import { useSectionLoading } from '@/composables/common';
import { Routes } from '@/router/routes';
import { useNonFungibleBalancesStore } from '@/store/balances/non-fungible';
import { useFrontendSettingsStore } from '@/store/settings/frontend';
import { useGeneralSettingsStore } from '@/store/settings/general';
import { useStatisticsStore } from '@/store/statistics';
import { DashboardTableType } from '@/types/frontend-settings';
import { Section } from '@/types/status';
import { TableColumn } from '@/types/table-column';
import { calculatePercentage } from '@/utils/calculation';

const nonFungibleRoute = Routes.ACCOUNTS_BALANCES_NON_FUNGIBLE;

const statistics = useStatisticsStore();
const { totalNetWorthUsd } = storeToRefs(statistics);
const balancesStore = useNonFungibleBalancesStore();
const { nonFungibleBalances } = storeToRefs(balancesStore);
const { nonFungibleTotalValue, fetchNonFungibleBalances } = balancesStore;
const { isSectionRefreshing } = useSectionLoading();

const { currencySymbol } = storeToRefs(useGeneralSettingsStore());
const total = nonFungibleTotalValue();
const { tc } = useI18n();

const group = DashboardTableType.NFT;
const loading = isSectionRefreshing(Section.NON_FUNGIBLE_BALANCES);

const tableHeaders = computed<DataTableHeader[]>(() => {
  const visibleColumns = get(dashboardTablesVisibleColumns)[group];

  const headers: DataTableHeader[] = [
    {
      text: tc('common.name'),
      value: 'name',
      cellClass: 'text-no-wrap'
    },
    {
      text: tc('nft_balance_table.column.price_in_asset'),
      value: 'priceInAsset',
      align: 'end',
      width: '75%',
      class: 'text-no-wrap'
    },
    {
      text: tc('common.price_in_symbol', 0, {
        symbol: get(currencySymbol)
      }),
      value: 'usdPrice',
      align: 'end',
      class: 'text-no-wrap'
    }
  ];

  if (visibleColumns.includes(TableColumn.PERCENTAGE_OF_TOTAL_NET_VALUE)) {
    headers.push({
      text: tc('nft_balance_table.column.percentage'),
      value: 'percentageOfTotalNetValue',
      align: 'end',
      class: 'text-no-wrap',
      sortable: false
    });
  }

  if (visibleColumns.includes(TableColumn.PERCENTAGE_OF_TOTAL_CURRENT_GROUP)) {
    headers.push({
      text: tc(
        'dashboard_asset_table.headers.percentage_of_total_current_group',
        0,
        {
          group
        }
      ),
      value: 'percentageOfTotalCurrentGroup',
      align: 'end',
      class: 'text-no-wrap',
      sortable: false
    });
  }

  return headers;
});

const percentageOfTotalNetValue = (value: BigNumber) => {
  return calculatePercentage(value, get(totalNetWorthUsd) as BigNumber);
};

const percentageOfCurrentGroup = (value: BigNumber) => {
  return calculatePercentage(value, get(total));
};

const refresh = async () => {
  return await fetchNonFungibleBalances({ ignoreCache: true });
};

const { dashboardTablesVisibleColumns } = storeToRefs(
  useFrontendSettingsStore()
);

const filteredBalances = computed(() => {
  return get(nonFungibleBalances).filter(item => !item.isLp);
});
</script>
