<template>
  <card v-if="mappedBalances.length > 0" outlined-body>
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
    <data-table
      :headers="tableHeaders"
      :items="mappedBalances"
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
          :label="$t('nft_balance_table.row.total')"
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
  </card>
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
import { setupGeneralSettings } from '@/composables/session';
import { setupSettings } from '@/composables/settings';
import i18n from '@/i18n';
import { Routes } from '@/router/routes';
import { BalanceActions } from '@/store/balances/action-types';
import { NonFungibleBalance } from '@/store/balances/types';
import { Section } from '@/store/const';
import { useStatisticsStore } from '@/store/statistics';
import { useStore } from '@/store/utils';
import {
  DashboardTablesVisibleColumns,
  DashboardTableType
} from '@/types/frontend-settings';
import { TableColumn } from '@/types/table-column';
import { Zero } from '@/utils/bignumbers';

const tableHeaders = (
  currency: Ref<string>,
  dashboardTablesVisibleColumns: Ref<DashboardTablesVisibleColumns>
) => {
  return computed<DataTableHeader[]>(() => {
    const visibleColumns = get(dashboardTablesVisibleColumns)[
      DashboardTableType.NFT
    ];

    const headers: DataTableHeader[] = [
      {
        text: i18n.t('nft_balance_table.column.name').toString(),
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
          .t('nft_balance_table.column.price', {
            currency: get(currency)
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
        class: 'text-no-wrap'
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
        class: 'text-no-wrap'
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
    )
  },
  setup() {
    const store = useStore();
    const statistics = useStatisticsStore();
    const { totalNetWorthUsd } = storeToRefs(statistics);
    const balances = computed<NonFungibleBalance[]>(
      () => store.getters['balances/nfBalances']
    );

    const { shouldShowLoadingScreen } = setupStatusChecking();

    const { currencySymbol } = setupGeneralSettings();

    const calculatePercentage = (value: BigNumber, divider: BigNumber) => {
      const percentage = divider.isZero()
        ? 0
        : value.div(divider).multipliedBy(100);
      return percentage.toFixed(2);
    };

    const percentageOfTotalNetValue = (value: BigNumber) => {
      return calculatePercentage(value, get(totalNetWorthUsd) as BigNumber);
    };

    const percentageOfCurrentGroup = (value: BigNumber) => {
      return calculatePercentage(value, get(total));
    };

    const refresh = async () => {
      return await store.dispatch(
        `balances/${BalanceActions.FETCH_NF_BALANCES}`,
        true
      );
    };

    const total = computed(() => {
      return get(balances).reduce(
        (sum, value) => sum.plus(value.usdPrice),
        Zero
      );
    });

    const { dashboardTablesVisibleColumns } = setupSettings();

    const mappedBalances = computed(() => {
      return get(balances).map(balance => {
        return {
          ...balance,
          imageUrl: balance.imageUrl || '/assets/images/placeholder.svg'
        };
      });
    });

    return {
      mappedBalances,
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
