<script setup lang="ts">
import { Routes } from '@/router/routes';
import { DashboardTableType } from '@/types/settings/frontend-settings';
import { Section } from '@/types/status';
import { TableColumn } from '@/types/table-column';
import { getCollectionData } from '@/utils/collection';
import { calculatePercentage } from '@/utils/calculation';
import type { BigNumber } from '@rotki/common';
import type { DataTableColumn } from '@rotki/ui-library';
import type { IgnoredAssetsHandlingType } from '@/types/asset';
import type { NonFungibleBalance, NonFungibleBalancesRequestPayload } from '@/types/nfbalances';

const ignoredAssetsHandling: IgnoredAssetsHandlingType = 'exclude';

const extraParams = computed(() => ({ ignoredAssetsHandling }));

const nonFungibleRoute = Routes.ACCOUNTS_BALANCES_NON_FUNGIBLE;

const statistics = useStatisticsStore();
const { totalNetWorthUsd } = storeToRefs(statistics);
const { fetchNonFungibleBalances, refreshNonFungibleBalances } = useNonFungibleBalancesStore();
const { dashboardTablesVisibleColumns } = storeToRefs(useFrontendSettingsStore());
const { currencySymbol } = storeToRefs(useGeneralSettingsStore());
const { t } = useI18n();

const group = DashboardTableType.NFT;

const {
  state: balances,
  isLoading,
  fetchData,
  setPage,
  pagination,
  sort,
} = usePaginationFilters<
  NonFungibleBalance,
  NonFungibleBalancesRequestPayload
>(fetchNonFungibleBalances, {
  extraParams,
  defaultSortBy: [{
    column: 'usdPrice',
    direction: 'desc',
  }],
});

const { isLoading: isSectionLoading } = useStatusStore();
const loading = isSectionLoading(Section.NON_FUNGIBLE_BALANCES);
const { totalUsdValue } = getCollectionData<NonFungibleBalance>(balances);

const tableHeaders = computed<DataTableColumn<NonFungibleBalance>[]>(() => {
  const visibleColumns = get(dashboardTablesVisibleColumns)[group];

  const headers: DataTableColumn<NonFungibleBalance>[] = [
    {
      label: t('common.name'),
      key: 'name',
      class: 'text-no-wrap w-full',
      cellClass: 'py-0',
      sortable: true,
    },
    {
      label: t('nft_balance_table.column.price_in_asset'),
      key: 'priceInAsset',
      align: 'end',
      class: 'text-no-wrap',
      cellClass: 'py-0',
    },
    {
      label: t('common.price_in_symbol', {
        symbol: get(currencySymbol),
      }),
      key: 'usdPrice',
      align: 'end',
      class: 'text-no-wrap',
      cellClass: 'py-0',
      sortable: true,
    },
  ];

  if (visibleColumns.includes(TableColumn.PERCENTAGE_OF_TOTAL_NET_VALUE)) {
    headers.push({
      label: t('nft_balance_table.column.percentage'),
      key: 'percentageOfTotalNetValue',
      align: 'end',
      class: 'text-no-wrap',
      cellClass: 'py-0',
    });
  }

  if (visibleColumns.includes(TableColumn.PERCENTAGE_OF_TOTAL_CURRENT_GROUP)) {
    headers.push({
      label: t('dashboard_asset_table.headers.percentage_of_total_current_group', {
        group,
      }),
      key: 'percentageOfTotalCurrentGroup',
      align: 'end',
      class: 'text-no-wrap',
      cellClass: 'py-0',
    });
  }

  return headers;
});

function percentageOfTotalNetValue(value: BigNumber) {
  return calculatePercentage(value, get(totalNetWorthUsd));
}

function percentageOfCurrentGroup(value: BigNumber) {
  return calculatePercentage(value, get(totalUsdValue) as BigNumber);
}

onMounted(async () => {
  await fetchData();
  await refreshNonFungibleBalances();
});

watch(loading, async (isLoading, wasLoading) => {
  if (!isLoading && wasLoading)
    await fetchData();
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
        <RuiButton
          variant="text"
          icon
          class="ml-2"
        >
          <RuiIcon name="arrow-right-s-line" />
        </RuiButton>
      </RouterLink>
    </template>
    <template #details>
      <VisibleColumnsSelector :group="group" />
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

    <CollectionHandler
      :collection="balances"
      @set-page="setPage($event)"
    >
      <template #default="{ data }">
        <RuiDataTable
          v-model:sort.external="sort"
          v-model:pagination.external="pagination"
          :cols="tableHeaders"
          :rows="data"
          :loading="isLoading"
          :empty="{ description: t('data_table.no_data') }"
          row-attr="id"
          sticky-header
          outlined
          dense
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
          <template #item.usdPrice="{ row }">
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
