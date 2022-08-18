<template>
  <dashboard-expandable-table>
    <template #title>
      {{ $t('nft_balance_table.title') }}
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
            :tooltip="$t('dashboard_asset_table.select_visible_columns')"
            class-name="ml-4 nft_balance_table__column-filter__button"
            :on-menu="on"
          >
            <v-icon>mdi-dots-vertical</v-icon>
          </menu-tooltip-button>
        </template>
        <visible-columns-selector group="NFT" />
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
          v-if="item.priceAsset !== currency"
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
          :label="$t('common.total')"
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

<script lang="ts">
import { BigNumber } from '@rotki/common';
import {
  computed,
  defineAsyncComponent,
  defineComponent,
  Ref
} from '@vue/composition-api';
import { get } from '@vueuse/core';
import { storeToRefs } from 'pinia';
import { DataTableHeader } from 'vuetify';
import { setupStatusChecking } from '@/composables/common';
import i18n from '@/i18n';
import { Routes } from '@/router/routes';
import { useBalancesStore } from '@/store/balances';
import { Section } from '@/store/const';
import { useFrontendSettingsStore } from '@/store/settings/frontend';
import { useGeneralSettingsStore } from '@/store/settings/general';
import { useStatisticsStore } from '@/store/statistics';
import {
  DashboardTablesVisibleColumns,
  DashboardTableType
} from '@/types/frontend-settings';
import { TableColumn } from '@/types/table-column';
import { calculatePercentage } from '@/utils/calculation';

const tableHeaders = (
  symbol: Ref<string>,
  dashboardTablesVisibleColumns: Ref<DashboardTablesVisibleColumns>
) => {
  return computed<DataTableHeader[]>(() => {
    const visibleColumns = get(dashboardTablesVisibleColumns)[
      DashboardTableType.NFT
    ];

    const headers: DataTableHeader[] = [
      {
        text: i18n.t('common.name').toString(),
        value: 'name',
        cellClass: 'text-no-wrap'
      },
      {
        text: i18n.t('nft_balance_table.column.price_in_asset').toString(),
        value: 'priceInAsset',
        align: 'end',
        width: '75%',
        class: 'text-no-wrap'
      },
      {
        text: i18n
          .t('common.price_in_symbol', {
            symbol: get(symbol)
          })
          .toString(),
        value: 'usdPrice',
        align: 'end',
        class: 'text-no-wrap'
      }
    ];

    if (visibleColumns.includes(TableColumn.PERCENTAGE_OF_TOTAL_NET_VALUE)) {
      headers.push({
        text: i18n.t('nft_balance_table.column.percentage').toString(),
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
        text: i18n
          .t(
            'dashboard_asset_table.headers.percentage_of_total_current_group',
            {
              group: 'NFT'
            }
          )
          .toString(),
        value: 'percentageOfTotalCurrentGroup',
        align: 'end',
        class: 'text-no-wrap',
        sortable: false
      });
    }

    return headers;
  });
};

export default defineComponent({
  name: 'NftBalanceTable',
  components: {
    NftDetails: defineAsyncComponent(
      () => import('@/components/helper/NftDetails.vue')
    ),
    RowAppend: defineAsyncComponent(
      () => import('@/components/helper/RowAppend.vue')
    ),
    VisibleColumnsSelector: defineAsyncComponent(
      () => import('@/components/dashboard/VisibleColumnsSelector.vue')
    ),
    MenuTooltipButton: defineAsyncComponent(
      () => import('@/components/helper/MenuTooltipButton.vue')
    ),
    DashboardExpandableTable: defineAsyncComponent(
      () => import('@/components/dashboard/DashboardExpandableTable.vue')
    )
  },
  setup() {
    const statistics = useStatisticsStore();
    const { totalNetWorthUsd } = storeToRefs(statistics);
    const balancesStore = useBalancesStore();
    const { nfBalances: balances } = storeToRefs(balancesStore);
    const { nfTotalValue, fetchNfBalances } = balancesStore;

    const { shouldShowLoadingScreen } = setupStatusChecking();

    const { currencySymbol } = storeToRefs(useGeneralSettingsStore());

    const total = nfTotalValue();

    const percentageOfTotalNetValue = (value: BigNumber) => {
      return calculatePercentage(value, get(totalNetWorthUsd) as BigNumber);
    };

    const percentageOfCurrentGroup = (value: BigNumber) => {
      return calculatePercentage(value, get(total));
    };

    const refresh = async () => {
      return await fetchNfBalances(true);
    };

    const { dashboardTablesVisibleColumns } = storeToRefs(
      useFrontendSettingsStore()
    );

    const filteredBalances = computed(() => {
      return get(balances).filter(item => !item.isLp);
    });

    return {
      filteredBalances,
      tableHeaders: tableHeaders(currencySymbol, dashboardTablesVisibleColumns),
      currency: currencySymbol,
      refresh,
      total,
      loading: shouldShowLoadingScreen(Section.NON_FUNGIBLE_BALANCES),
      nonFungibleRoute: Routes.ACCOUNTS_BALANCES_NON_FUNGIBLE.route,
      percentageOfTotalNetValue,
      percentageOfCurrentGroup
    };
  }
});
</script>
