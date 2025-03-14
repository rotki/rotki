<script setup lang="ts">
import type { IgnoredAssetsHandlingType } from '@/types/asset';
import type { NonFungibleBalance, NonFungibleBalancesRequestPayload } from '@/types/nfbalances';
import type { BigNumber } from '@rotki/common';
import type { DataTableColumn } from '@rotki/ui-library';
import DashboardExpandableTable from '@/components/dashboard/DashboardExpandableTable.vue';
import VisibleColumnsSelector from '@/components/dashboard/VisibleColumnsSelector.vue';
import AmountDisplay from '@/components/display/amount/AmountDisplay.vue';
import PercentageDisplay from '@/components/display/PercentageDisplay.vue';
import CollectionHandler from '@/components/helper/CollectionHandler.vue';
import NftDetails from '@/components/helper/NftDetails.vue';
import RefreshButton from '@/components/helper/RefreshButton.vue';
import RowAppend from '@/components/helper/RowAppend.vue';
import { usePaginationFilters } from '@/composables/use-pagination-filter';
import { useNftBalances } from '@/modules/balances/nft/use-nft-balances';
import { Routes } from '@/router/routes';
import { useFrontendSettingsStore } from '@/store/settings/frontend';
import { useGeneralSettingsStore } from '@/store/settings/general';
import { useStatisticsStore } from '@/store/statistics';
import { useStatusStore } from '@/store/status';
import { DashboardTableType } from '@/types/settings/frontend-settings';
import { Section } from '@/types/status';
import { TableColumn } from '@/types/table-column';
import { calculatePercentage } from '@/utils/calculation';
import { getCollectionData } from '@/utils/collection';

const ignoredAssetsHandling: IgnoredAssetsHandlingType = 'exclude';

const extraParams = computed(() => ({ ignoredAssetsHandling }));

const nonFungibleRoute = Routes.BALANCES_NON_FUNGIBLE;

const statistics = useStatisticsStore();
const { totalNetWorthUsd } = storeToRefs(statistics);
const { fetchNonFungibleBalances, refreshNonFungibleBalances } = useNftBalances();
const { dashboardTablesVisibleColumns } = storeToRefs(useFrontendSettingsStore());
const { currencySymbol } = storeToRefs(useGeneralSettingsStore());
const { t } = useI18n();

const group = DashboardTableType.NFT;

const {
  fetchData,
  isLoading,
  pagination,
  setPage,
  sort,
  state: balances,
} = usePaginationFilters<
  NonFungibleBalance,
  NonFungibleBalancesRequestPayload
>(fetchNonFungibleBalances, {
  defaultSortBy: [{
    column: 'usdPrice',
    direction: 'desc',
  }],
  extraParams,
});

const { isLoading: isSectionLoading } = useStatusStore();
const loading = isSectionLoading(Section.NON_FUNGIBLE_BALANCES);
const { totalUsdValue } = getCollectionData<NonFungibleBalance>(balances);

const tableHeaders = computed<DataTableColumn<NonFungibleBalance>[]>(() => {
  const visibleColumns = get(dashboardTablesVisibleColumns)[group];

  const headers: DataTableColumn<NonFungibleBalance>[] = [
    {
      cellClass: 'py-0',
      class: 'text-no-wrap w-full',
      key: 'name',
      label: t('common.name'),
      sortable: true,
    },
    {
      align: 'end',
      cellClass: 'py-0',
      class: 'text-no-wrap',
      key: 'priceInAsset',
      label: t('nft_balance_table.column.price_in_asset'),
    },
    {
      align: 'end',
      cellClass: 'py-0',
      class: 'text-no-wrap',
      key: 'usdPrice',
      label: t('common.price_in_symbol', {
        symbol: get(currencySymbol),
      }),
      sortable: true,
    },
  ];

  if (visibleColumns.includes(TableColumn.PERCENTAGE_OF_TOTAL_NET_VALUE)) {
    headers.push({
      align: 'end',
      cellClass: 'py-0',
      class: 'text-no-wrap',
      key: 'percentageOfTotalNetValue',
      label: t('nft_balance_table.column.percentage'),
    });
  }

  if (visibleColumns.includes(TableColumn.PERCENTAGE_OF_TOTAL_CURRENT_GROUP)) {
    headers.push({
      align: 'end',
      cellClass: 'py-0',
      class: 'text-no-wrap',
      key: 'percentageOfTotalCurrentGroup',
      label: t('dashboard_asset_table.headers.percentage_of_total_current_group', {
        group,
      }),
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
          <RuiIcon name="lu-chevron-right" />
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
