<script setup lang="ts">
import { type BigNumber } from '@rotki/common';
import { type DataTableHeader } from '@/types/vuetify';
import { type IgnoredAssetsHandlingType } from '@/types/asset';
import { Routes } from '@/router/routes';
import { DashboardTableType } from '@/types/settings/frontend-settings';
import {
  type NonFungibleBalance,
  type NonFungibleBalanceWithLastPrice,
  type NonFungibleBalancesRequestPayload
} from '@/types/nfbalances';
import { Section } from '@/types/status';
import { TableColumn } from '@/types/table-column';

const ignoredAssetsHandling: IgnoredAssetsHandlingType = 'exclude';

const extraParams = computed(() => ({ ignoredAssetsHandling }));

const nonFungibleRoute = Routes.ACCOUNTS_BALANCES_NON_FUNGIBLE;

const statistics = useStatisticsStore();
const { totalNetWorthUsd } = storeToRefs(statistics);
const { fetchNonFungibleBalances, refreshNonFungibleBalances } =
  useNonFungibleBalancesStore();

const { currencySymbol } = storeToRefs(useGeneralSettingsStore());
const { t } = useI18n();

const group = DashboardTableType.NFT;

const {
  state: balances,
  isLoading,
  options,
  fetchData,
  setPage,
  setOptions
} = usePaginationFilters<
  NonFungibleBalance,
  NonFungibleBalancesRequestPayload,
  NonFungibleBalanceWithLastPrice
>(null, false, useEmptyFilter, fetchNonFungibleBalances, {
  extraParams,
  defaultSortBy: {
    key: 'lastPrice',
    ascending: [false]
  }
});

const { isLoading: isSectionLoading } = useStatusStore();
const loading = isSectionLoading(Section.NON_FUNGIBLE_BALANCES);

const tableHeaders = computed<DataTableHeader[]>(() => {
  const visibleColumns = get(dashboardTablesVisibleColumns)[group];

  const headers: DataTableHeader[] = [
    {
      text: t('common.name'),
      value: 'name',
      class: 'text-no-wrap'
    },
    {
      text: t('nft_balance_table.column.price_in_asset'),
      value: 'priceInAsset',
      align: 'end',
      width: '75%',
      class: 'text-no-wrap',
      sortable: false
    },
    {
      text: t('common.price_in_symbol', {
        symbol: get(currencySymbol)
      }),
      value: 'lastPrice',
      align: 'end',
      class: 'text-no-wrap'
    }
  ];

  if (visibleColumns.includes(TableColumn.PERCENTAGE_OF_TOTAL_NET_VALUE)) {
    headers.push({
      text: t('nft_balance_table.column.percentage'),
      value: 'percentageOfTotalNetValue',
      align: 'end',
      class: 'text-no-wrap',
      sortable: false
    });
  }

  if (visibleColumns.includes(TableColumn.PERCENTAGE_OF_TOTAL_CURRENT_GROUP)) {
    headers.push({
      text: t(
        'dashboard_asset_table.headers.percentage_of_total_current_group',
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

const percentageOfTotalNetValue = (value: BigNumber) =>
  calculatePercentage(value, get(totalNetWorthUsd) as BigNumber);

const percentageOfCurrentGroup = (value: BigNumber) =>
  calculatePercentage(value, get(totalUsdValue) as BigNumber);

const { dashboardTablesVisibleColumns } = storeToRefs(
  useFrontendSettingsStore()
);

const { totalUsdValue } = getCollectionData<NonFungibleBalance>(balances);

onMounted(async () => {
  await fetchData();
  await refreshNonFungibleBalances();
});

watch(loading, async (isLoading, wasLoading) => {
  if (!isLoading && wasLoading) {
    await fetchData();
  }
});
</script>

<template>
  <DashboardExpandableTable>
    <template #title>
      <RefreshButton
        :loading="loading"
        :tooltip="t('nft_balance_table.refresh')"
        @refresh="refreshNonFungibleBalances(true)"
      />
      {{ t('nft_balance_table.title') }}
      <VBtn :to="nonFungibleRoute" icon class="ml-2">
        <VIcon>mdi-chevron-right</VIcon>
      </VBtn>
    </template>
    <template #details>
      <VMenu
        id="nft_balance_table__column-filter"
        transition="slide-y-transition"
        max-width="250px"
        offset-y
      >
        <template #activator="{ on }">
          <MenuTooltipButton
            :tooltip="t('dashboard_asset_table.select_visible_columns')"
            class-name="ml-4 nft_balance_table__column-filter__button"
            :on-menu="on"
          >
            <VIcon>mdi-dots-vertical</VIcon>
          </MenuTooltipButton>
        </template>
        <VisibleColumnsSelector :group="group" />
      </VMenu>
    </template>
    <template #shortDetails>
      <AmountDisplay
        :value="totalUsdValue"
        show-currency="symbol"
        fiat-currency="USD"
      />
    </template>

    <CollectionHandler :collection="balances" @set-page="setPage($event)">
      <template #default="{ data, itemLength }">
        <DataTable
          :headers="tableHeaders"
          :items="data"
          :loading="isLoading"
          :options="options"
          :server-items-length="itemLength"
          @update:options="setOptions($event)"
        >
          <template #item.name="{ item }">
            <NftDetails :identifier="item.id" />
          </template>
          <template #item.priceInAsset="{ item }">
            <AmountDisplay
              v-if="item.priceAsset !== currencySymbol"
              :value="item.priceInAsset"
              :asset="item.priceAsset"
            />
            <span v-else>-</span>
          </template>
          <template #item.lastPrice="{ item }">
            <AmountDisplay
              no-scramble
              :price-asset="item.priceAsset"
              :amount="item.priceInAsset"
              :value="item.usdPrice"
              show-currency="symbol"
              fiat-currency="USD"
            />
          </template>
          <template #item.percentageOfTotalNetValue="{ item }">
            <PercentageDisplay
              :value="percentageOfTotalNetValue(item.usdPrice)"
            />
          </template>
          <template #item.percentageOfTotalCurrentGroup="{ item }">
            <PercentageDisplay
              :value="percentageOfCurrentGroup(item.usdPrice)"
            />
          </template>
          <template #body.append="{ isMobile }">
            <RowAppend
              label-colspan="2"
              :label="t('common.total')"
              :right-patch-colspan="tableHeaders.length - 3"
              :is-mobile="isMobile"
            >
              <AmountDisplay
                :value="totalUsdValue"
                show-currency="symbol"
                fiat-currency="USD"
              />
            </RowAppend>
          </template>
        </DataTable>
      </template>
    </CollectionHandler>
  </DashboardExpandableTable>
</template>
