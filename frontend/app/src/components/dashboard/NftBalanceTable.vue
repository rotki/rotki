<script setup lang="ts">
import { type BigNumber } from '@rotki/common';
import {
  type DataTableColumn,
  type DataTableSortColumn
} from '@rotki/ui-library-compat';
import { type Ref } from 'vue';
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

const sort: Ref<DataTableSortColumn | DataTableSortColumn[] | undefined> = ref({
  column: 'lastPrice',
  direction: 'desc' as const
});

const group = DashboardTableType.NFT;

const {
  state: balances,
  isLoading,
  options,
  fetchData,
  setPage,
  setTableOptions
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

const tableHeaders = computed<DataTableColumn[]>(() => {
  const visibleColumns = get(dashboardTablesVisibleColumns)[group];

  const headers: DataTableColumn[] = [
    {
      label: t('common.name'),
      key: 'name',
      class: 'text-no-wrap',
      cellClass: 'py-0',
      sortable: true
    },
    {
      label: t('nft_balance_table.column.price_in_asset'),
      key: 'priceInAsset',
      align: 'end',
      class: 'text-no-wrap',
      cellClass: 'py-0'
    },
    {
      label: t('common.price_in_symbol', {
        symbol: get(currencySymbol)
      }),
      key: 'lastPrice',
      align: 'end',
      class: 'text-no-wrap',
      cellClass: 'py-0',
      sortable: true
    }
  ];

  if (visibleColumns.includes(TableColumn.PERCENTAGE_OF_TOTAL_NET_VALUE)) {
    headers.push({
      label: t('nft_balance_table.column.percentage'),
      key: 'percentageOfTotalNetValue',
      align: 'end',
      class: 'text-no-wrap',
      cellClass: 'py-0'
    });
  }

  if (visibleColumns.includes(TableColumn.PERCENTAGE_OF_TOTAL_CURRENT_GROUP)) {
    headers.push({
      label: t(
        'dashboard_asset_table.headers.percentage_of_total_current_group',
        {
          group
        }
      ),
      key: 'percentageOfTotalCurrentGroup',
      align: 'end',
      class: 'text-no-wrap',
      cellClass: 'py-0'
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
      <RouterLink :to="nonFungibleRoute">
        <RuiButton variant="text" icon class="ml-2">
          <RuiIcon name="arrow-right-s-line" />
        </RuiButton>
      </RouterLink>
    </template>
    <template #details>
      <VMenu
        id="nft_balance_table__column-filter"
        transition="slide-y-transition"
        max-width="250px"
        nudge-bottom="20"
        offset-y
        left
      >
        <template #activator="{ on }">
          <MenuTooltipButton
            :tooltip="t('dashboard_asset_table.select_visible_columns')"
            class-name="nft_balance_table__column-filter__button"
            v-on="on"
          >
            <RuiIcon name="more-2-fill" />
          </MenuTooltipButton>
        </template>
        <VisibleColumnsSelector :group="group" />
      </VMenu>
    </template>
    <template #shortDetails>
      <AmountDisplay
        v-if="totalUsdValue"
        :value="totalUsdValue"
        show-currency="symbol"
        fiat-currency="USD"
        class="text-h6 font-bold"
      />
    </template>

    <CollectionHandler :collection="balances" @set-page="setPage($event)">
      <template #default="{ data, itemLength }">
        <RuiDataTable
          :cols="tableHeaders"
          :rows="data"
          :loading="isLoading"
          :options="options"
          :sort.sync="sort"
          :pagination="{
            limit: options.itemsPerPage,
            page: options.page,
            total: itemLength
          }"
          :pagination-modifiers="{ external: true }"
          :sort-modifiers="{ external: true }"
          :empty="{ description: t('data_table.no_data') }"
          :sticky-offset="64"
          row-attr="id"
          sticky-header
          outlined
          @update:options="setTableOptions($event)"
        >
          <template #item.name="{ row }">
            <NftDetails :identifier="row.id" />
          </template>
          <template #item.priceInAsset="{ row }">
            <AmountDisplay
              v-if="row.priceAsset !== currencySymbol"
              :value="row.priceInAsset"
              :asset="row.priceAsset"
            />
            <span v-else>-</span>
          </template>
          <template #item.lastPrice="{ row }">
            <AmountDisplay
              no-scramble
              :price-asset="row.priceAsset"
              :amount="row.priceInAsset"
              :value="row.usdPrice"
              show-currency="symbol"
              fiat-currency="USD"
            />
          </template>
          <template #item.percentageOfTotalNetValue="{ row }">
            <PercentageDisplay
              :value="percentageOfTotalNetValue(row.usdPrice)"
              :asset-padding="0.1"
            />
          </template>
          <template #item.percentageOfTotalCurrentGroup="{ row }">
            <PercentageDisplay
              :value="percentageOfCurrentGroup(row.usdPrice)"
              :asset-padding="0.1"
            />
          </template>
          <template #body.append>
            <RowAppend
              label-colspan="2"
              :label="t('common.total')"
              :right-patch-colspan="tableHeaders.length - 3"
              :is-mobile="false"
              class-name="[&>td]:p-4 text-sm"
            >
              <AmountDisplay
                v-if="totalUsdValue"
                :value="totalUsdValue"
                show-currency="symbol"
                fiat-currency="USD"
              />
            </RowAppend>
          </template>
        </RuiDataTable>
      </template>
    </CollectionHandler>
  </DashboardExpandableTable>
</template>
