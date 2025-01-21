<script setup lang="ts">
import { isEqual } from 'es-toolkit';
import { type BigNumber, Blockchain, type XSwapLiquidityBalance, type XswapAsset } from '@rotki/common';
import { Routes } from '@/router/routes';
import { DashboardTableType, type DashboardTablesVisibleColumns } from '@/types/settings/frontend-settings';
import { Section } from '@/types/status';
import { TableColumn } from '@/types/table-column';
import { calculatePercentage } from '@/utils/calculation';
import { useStatisticsStore } from '@/store/statistics';
import { useBlockchainStore } from '@/store/blockchain';
import { useStatusStore } from '@/store/status';
import { useFrontendSettingsStore } from '@/store/settings/frontend';
import { useGeneralSettingsStore } from '@/store/settings/general';
import { useSushiswapStore } from '@/store/defi/sushiswap';
import { useUniswapStore } from '@/store/defi/uniswap';
import { useLiquidityPosition } from '@/composables/defi';
import { usePremium } from '@/composables/premium';
import AmountDisplay from '@/components/display/amount/AmountDisplay.vue';
import RowAppend from '@/components/helper/RowAppend.vue';
import LiquidityProviderBalanceDetails
  from '@/components/dashboard/liquity-provider/LiquidityProviderBalanceDetails.vue';
import PercentageDisplay from '@/components/display/PercentageDisplay.vue';
import LpPoolIcon from '@/components/display/defi/LpPoolIcon.vue';
import NftDetails from '@/components/helper/NftDetails.vue';
import VisibleColumnsSelector from '@/components/dashboard/VisibleColumnsSelector.vue';
import RefreshButton from '@/components/helper/RefreshButton.vue';
import DashboardExpandableTable from '@/components/dashboard/DashboardExpandableTable.vue';
import type { DataTableColumn, DataTableSortData } from '@rotki/ui-library';

const { t } = useI18n();
const LIQUIDITY_POSITION = DashboardTableType.LIQUIDITY_POSITION;

const sort = ref<DataTableSortData<XSwapLiquidityBalance>>({
  column: 'usdValue',
  direction: 'desc' as const,
});

function createTableHeaders(currency: Ref<string>, dashboardTablesVisibleColumns: Ref<DashboardTablesVisibleColumns>) {
  return computed<DataTableColumn<XSwapLiquidityBalance>[]>(() => {
    const visibleColumns = get(dashboardTablesVisibleColumns)[LIQUIDITY_POSITION];

    const headers: DataTableColumn<XSwapLiquidityBalance>[] = [
      {
        cellClass: 'text-no-wrap',
        key: 'name',
        label: t('common.name'),
      },
      {
        align: 'end',
        class: 'text-no-wrap',
        key: 'usdValue',
        label: t('common.value_in_symbol', {
          symbol: get(currency),
        }),
      },
    ];

    if (visibleColumns.includes(TableColumn.PERCENTAGE_OF_TOTAL_NET_VALUE)) {
      headers.push({
        align: 'end',
        class: 'text-no-wrap',
        key: 'percentageOfTotalNetValue',
        label: t('dashboard_asset_table.headers.percentage_of_total_net_value'),
      });
    }

    if (visibleColumns.includes(TableColumn.PERCENTAGE_OF_TOTAL_CURRENT_GROUP)) {
      headers.push({
        align: 'end',
        class: 'text-no-wrap',
        key: 'percentageOfTotalCurrentGroup',
        label: t('dashboard_asset_table.headers.percentage_of_total_current_group', {
          group: t('dashboard.liquidity_position.title'),
        }),
      });
    }

    return headers;
  });
}

const route = Routes.DEFI_DEPOSITS_LIQUIDITY;
const expanded = ref<XSwapLiquidityBalance[]>([]);

const { fetchV2Balances: fetchUniswapV2Balances } = useUniswapStore();

const { fetchBalances: fetchSushiswapBalances } = useSushiswapStore();

const { getPoolName, lpAggregatedBalances: balances, lpTotal: totalInUsd } = useLiquidityPosition();

const { currencySymbol } = storeToRefs(useGeneralSettingsStore());
const { dashboardTablesVisibleColumns } = storeToRefs(useFrontendSettingsStore());

const tableHeaders = createTableHeaders(currencySymbol, dashboardTablesVisibleColumns);

const { isLoading } = useStatusStore();

const loading = logicOr(
  isLoading(Section.DEFI_UNISWAP_V2_BALANCES),
  isLoading(Section.DEFI_SUSHISWAP_BALANCES),
);

const statistics = useStatisticsStore();
const { totalNetWorthUsd } = storeToRefs(statistics);

function percentageOfTotalNetValue(value: BigNumber) {
  const netWorth = get(totalNetWorthUsd);
  const total = netWorth.lt(0) ? get(totalInUsd) : netWorth;
  return calculatePercentage(value, total);
}

function percentageOfCurrentGroup(value: BigNumber) {
  return calculatePercentage(value, get(totalInUsd));
}

const premium = usePremium();

const chainStore = useBlockchainStore();
const ethAddresses = computed<string[]>(() => chainStore.getAddresses(Blockchain.ETH));

async function fetch(refresh = false) {
  if (get(ethAddresses).length > 0) {
    await fetchUniswapV2Balances(refresh);

    if (get(premium)) {
      await fetchSushiswapBalances(refresh);
    }
  }
}

onBeforeMount(async () => {
  await fetch();
});

watch(ethAddresses, async (curr, prev) => {
  if (!isEqual(curr, prev))
    await fetch(true);
});

watch(premium, async (curr, prev) => {
  if (prev !== curr)
    await fetch(true);
});

const getAssets = (assets: XswapAsset[]) => assets.map(({ asset }) => asset);
</script>

<template>
  <DashboardExpandableTable v-if="balances.length > 0">
    <template #title>
      <RefreshButton
        :loading="loading"
        :tooltip="t('dashboard.liquidity_position.refresh_tooltip')"
        @refresh="fetch(true)"
      />
      {{ t('dashboard.liquidity_position.title') }}
      <RouterLink :to="route">
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
      <VisibleColumnsSelector
        :group="LIQUIDITY_POSITION"
        :group-label="t('dashboard.liquidity_position.title')"
      />
    </template>
    <template #shortDetails>
      <AmountDisplay
        :value="totalInUsd"
        show-currency="symbol"
        fiat-currency="USD"
        class="text-h6 font-bold"
      />
    </template>
    <RuiDataTable
      v-model:expanded="expanded"
      outlined
      dense
      :cols="tableHeaders"
      :rows="balances"
      :sort="sort"
      :loading="loading"
      row-attr="id"
      single-expand
    >
      <template #item.name="{ row }">
        <div v-if="row.type === 'nft'">
          <NftDetails
            :identifier="row.asset"
            :styled="{ margin: '1px 4px' }"
          />
        </div>

        <div
          v-else
          class="flex items-center py-2"
        >
          <LpPoolIcon
            :type="row.lpType"
            :assets="getAssets(row.assets)"
          />
          <div class="pl-4 font-medium">
            {{ getPoolName(row.lpType, getAssets(row.assets)) }}
          </div>
        </div>
      </template>
      <template #item.usdValue="{ row }">
        <AmountDisplay
          :value="row.usdValue"
          fiat-currency="USD"
        />
      </template>
      <template #item.percentageOfTotalNetValue="{ row }">
        <PercentageDisplay
          :value="percentageOfTotalNetValue(row.usdValue)"
          :asset-padding="0.1"
        />
      </template>
      <template #item.percentageOfTotalCurrentGroup="{ row }">
        <PercentageDisplay
          :value="percentageOfCurrentGroup(row.usdValue)"
          :asset-padding="0.1"
        />
      </template>
      <template #expanded-item="{ row }">
        <LiquidityProviderBalanceDetails
          :assets="row.assets"
          :premium-only="row.premiumOnly"
        />
      </template>
      <template #body.append>
        <RowAppend
          label-colspan="1"
          :label="t('common.total')"
          :right-patch-colspan="tableHeaders.length - 2"
          class-name="[&>td]:p-4"
        >
          <AmountDisplay
            :value="totalInUsd"
            show-currency="symbol"
            fiat-currency="USD"
          />
        </RowAppend>
      </template>
    </RuiDataTable>
  </DashboardExpandableTable>
</template>
