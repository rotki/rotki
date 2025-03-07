<script setup lang="ts">
import type { BigNumber } from '@rotki/common';
import type { DataTableColumn, DataTableSortData } from '@rotki/ui-library';
import type { PoolAsset, PoolLiquidityBalance } from './types';
import DashboardExpandableTable from '@/components/dashboard/DashboardExpandableTable.vue';
import VisibleColumnsSelector from '@/components/dashboard/VisibleColumnsSelector.vue';
import AmountDisplay from '@/components/display/amount/AmountDisplay.vue';
import PercentageDisplay from '@/components/display/PercentageDisplay.vue';
import RefreshButton from '@/components/helper/RefreshButton.vue';
import RowAppend from '@/components/helper/RowAppend.vue';
import PoolDetails from '@/modules/dashboard/liquidity-pools/PoolDetails.vue';
import PoolIcon from '@/modules/dashboard/liquidity-pools/PoolIcon.vue';
import { useFrontendSettingsStore } from '@/store/settings/frontend';
import { useGeneralSettingsStore } from '@/store/settings/general';
import { useStatisticsStore } from '@/store/statistics';
import { DashboardTableType } from '@/types/settings/frontend-settings';
import { TableColumn } from '@/types/table-column';
import { calculatePercentage } from '@/utils/calculation';
import { usePoolBalances } from './use-pool-balances';

const LIQUIDITY_POSITION = DashboardTableType.LIQUIDITY_POSITION;

const expanded = ref<PoolLiquidityBalance[]>([]);

const sort = ref<DataTableSortData<PoolLiquidityBalance>>({
  column: 'usdValue',
  direction: 'desc' as const,
});

const { currencySymbol } = storeToRefs(useGeneralSettingsStore());
const { dashboardTablesVisibleColumns } = storeToRefs(useFrontendSettingsStore());
const statistics = useStatisticsStore();
const { totalNetWorthUsd } = storeToRefs(statistics);
const { balances, fetch, getPoolName, loading, total: totalInUsd } = usePoolBalances();
const { t } = useI18n();

const tableHeaders = computed<DataTableColumn<PoolLiquidityBalance>[]>(() => {
  const visibleColumns = get(dashboardTablesVisibleColumns)[LIQUIDITY_POSITION];

  const headers: DataTableColumn<PoolLiquidityBalance>[] = [{
    cellClass: 'text-no-wrap',
    key: 'name',
    label: t('common.name'),
  }, {
    align: 'end',
    class: 'text-no-wrap',
    key: 'usdValue',
    label: t('common.value_in_symbol', {
      symbol: get(currencySymbol),
    }),
  }];

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
        group: t('modules.dashboard.liquidity_pools.pool_table.title'),
      }),
    });
  }

  return headers;
});

const getAssets = (assets: PoolAsset[]) => assets.map(({ asset }) => asset);

function percentageOfTotalNetValue(value: BigNumber) {
  const netWorth = get(totalNetWorthUsd);
  const total = netWorth.lt(0) ? get(totalInUsd) : netWorth;
  return calculatePercentage(value, total);
}

function percentageOfCurrentGroup(value: BigNumber) {
  return calculatePercentage(value, get(totalInUsd));
}

onBeforeMount(async () => {
  await fetch();
});
</script>

<template>
  <DashboardExpandableTable v-if="balances.length > 0">
    <template #title>
      <RefreshButton
        :loading="loading"
        :tooltip="t('modules.dashboard.liquidity_pools.pool_table.refresh_tooltip')"
        @refresh="fetch(true)"
      />
      {{ t('modules.dashboard.liquidity_pools.pool_table.title') }}
    </template>
    <template #details>
      <VisibleColumnsSelector
        :group="LIQUIDITY_POSITION"
        :group-label="t('modules.dashboard.liquidity_pools.pool_table.title')"
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
        <div class="flex items-center py-2">
          <PoolIcon
            :type="row.type"
            :assets="getAssets(row.assets)"
          />
          <div class="pl-4 font-medium">
            {{ getPoolName(row.type, getAssets(row.assets)) }}
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
        <PoolDetails
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
