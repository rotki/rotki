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
import { TableId, useRememberTableSorting } from '@/modules/table/use-remember-table-sorting';
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
  column: 'value',
  direction: 'desc' as const,
});

const { currencySymbol } = storeToRefs(useGeneralSettingsStore());
const { dashboardTablesVisibleColumns } = storeToRefs(useFrontendSettingsStore());
const statistics = useStatisticsStore();
const { totalNetWorth } = storeToRefs(statistics);
const { balances, fetch, getPoolName, loading, total } = usePoolBalances();
const { t } = useI18n({ useScope: 'global' });

const tableHeaders = computed<DataTableColumn<PoolLiquidityBalance>[]>(() => {
  const visibleColumns = get(dashboardTablesVisibleColumns)[LIQUIDITY_POSITION];

  const headers: DataTableColumn<PoolLiquidityBalance>[] = [{
    cellClass: 'text-no-wrap',
    key: 'name',
    label: t('common.name'),
  }, {
    align: 'end',
    class: 'text-no-wrap',
    key: 'value',
    label: t('common.value_in_symbol', {
      symbol: get(currencySymbol),
    }),
    sortable: true,
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

useRememberTableSorting<PoolLiquidityBalance>(TableId.POOL_LIQUIDITY_BALANCE, sort, tableHeaders);

const getAssets = (assets: PoolAsset[]) => assets.map(({ asset }) => asset);

function percentageOfTotalNetValue(value: BigNumber) {
  const netWorth = get(totalNetWorth);
  const totalVal = netWorth.lt(0) ? get(total) : netWorth;
  return calculatePercentage(value, totalVal);
}

function percentageOfCurrentGroup(value: BigNumber) {
  return calculatePercentage(value, get(total));
}

onBeforeMount(async () => {
  await fetch();
});

watch(currencySymbol, async () => {
  await fetch(true);
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
        :value="total"
        show-currency="symbol"
        force-currency
        class="text-h6 font-bold"
      />
    </template>

    <RuiDataTable
      v-model:expanded="expanded"
      v-model:sort="sort"
      outlined
      dense
      :cols="tableHeaders"
      :rows="balances"
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
      <template #item.value="{ row }">
        <AmountDisplay
          :value="row.value"
          force-currency
        />
      </template>
      <template #item.percentageOfTotalNetValue="{ row }">
        <PercentageDisplay
          :value="percentageOfTotalNetValue(row.value)"
          :asset-padding="0.1"
        />
      </template>
      <template #item.percentageOfTotalCurrentGroup="{ row }">
        <PercentageDisplay
          :value="percentageOfCurrentGroup(row.value)"
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
            :value="total"
            show-currency="symbol"
            force-currency
          />
        </RowAppend>
      </template>
    </RuiDataTable>
  </DashboardExpandableTable>
</template>
