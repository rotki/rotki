<script setup lang="ts">
import type { BigNumber } from '@rotki/common';
import type { DataTableColumn, DataTableSortData } from '@rotki/ui-library';
import type { PoolAsset, PoolLiquidityBalance } from './types';
import { FiatDisplay } from '@/modules/assets/amount-display/components';
import { calculatePercentage } from '@/modules/core/common/data/calculation';
import { TableColumn } from '@/modules/core/table/table-column';
import { TableId, useRememberTableSorting } from '@/modules/core/table/use-remember-table-sorting';
import DashboardExpandableTable from '@/modules/dashboard/DashboardExpandableTable.vue';
import PoolDetails from '@/modules/dashboard/liquidity-pools/PoolDetails.vue';
import PoolIcon from '@/modules/dashboard/liquidity-pools/PoolIcon.vue';
import VisibleColumnsSelector from '@/modules/dashboard/VisibleColumnsSelector.vue';
import { fitsEveryLimit } from '@/modules/session/use-items-per-page';
import { DashboardTableType } from '@/modules/settings/types/frontend-settings';
import { useSetting } from '@/modules/settings/use-setting';
import PercentageDisplay from '@/modules/shell/components/display/PercentageDisplay.vue';
import RowAppend from '@/modules/shell/components/RowAppend.vue';
import { useStatisticsStore } from '@/modules/statistics/use-statistics-store';
import { usePoolBalances } from './use-pool-balances';

const LIQUIDITY_POSITION = DashboardTableType.LIQUIDITY_POSITION;

const PAGE_SIZE = 10;

const expanded = ref<PoolLiquidityBalance[]>([]);

const sort = ref<DataTableSortData<PoolLiquidityBalance>>({
  column: 'value',
  direction: 'desc' as const,
});

const currencySymbol = useSetting('currencySymbol');
const dashboardTablesVisibleColumns = useSetting('dashboardTablesVisibleColumns');
const statistics = useStatisticsStore();
const { totalNetWorth } = storeToRefs(statistics);
const { balances, fetch, getPoolLabel, loading, total } = usePoolBalances();

const hidePagination = computed<boolean>(() => fitsEveryLimit(get(balances).length));
const { t } = useI18n({ useScope: 'global' });

const tableHeaders = computed<DataTableColumn<PoolLiquidityBalance>[]>(() => {
  const visibleColumns = get(dashboardTablesVisibleColumns)[LIQUIDITY_POSITION];

  const headers: DataTableColumn<PoolLiquidityBalance>[] = [{
    cellClass: 'text-no-wrap py-0',
    class: 'text-no-wrap w-full',
    key: 'name',
    label: t('common.name'),
  }, {
    align: 'end',
    cellClass: 'font-medium',
    class: 'text-no-wrap',
    key: 'value',
    label: t('common.value'),
    sortable: true,
  }];

  if (visibleColumns.includes(TableColumn.PERCENTAGE_OF_TOTAL_NET_VALUE)) {
    headers.push({
      align: 'end',
      cellClass: 'text-rui-text-secondary',
      class: 'text-no-wrap',
      key: 'percentageOfTotalNetValue',
      label: t('dashboard_asset_table.headers.percentage_of_total_net_value'),
    });
  }

  if (visibleColumns.includes(TableColumn.PERCENTAGE_OF_TOTAL_CURRENT_GROUP)) {
    headers.push({
      align: 'end',
      cellClass: 'text-rui-text-secondary',
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

const poolLabels = computed<Map<number, ReturnType<typeof getPoolLabel>>>(() => new Map(
  get(balances).map(row => [row.id, getPoolLabel(row.type, getAssets(row.assets))]),
));

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
  <DashboardExpandableTable
    v-if="balances.length > 0"
    :count="balances.length"
  >
    <template #title>
      {{ t('modules.dashboard.liquidity_pools.pool_table.title') }}
    </template>
    <template #details>
      <VisibleColumnsSelector
        :group="LIQUIDITY_POSITION"
        :group-label="t('modules.dashboard.liquidity_pools.pool_table.title')"
        size="sm"
      />
    </template>
    <template #shortDetails>
      <FiatDisplay
        :value="total"
        class="text-h6 font-bold"
      />
    </template>

    <RuiDataTable
      v-model:expanded="expanded"
      v-model:sort="sort"
      dense
      :items-per-page="PAGE_SIZE"
      :hide-default-header="hidePagination"
      :hide-default-footer="hidePagination"
      class="!rounded-t-none"
      :class="{ 'border-t border-default': !hidePagination }"
      :cols="tableHeaders"
      :rows="balances"
      :loading="loading"
      row-attr="id"
      single-expand
    >
      <template #item.name="{ row }">
        <div class="flex items-center gap-3 py-2">
          <PoolIcon
            :type="row.type"
            :assets="getAssets(row.assets)"
          />
          <div class="flex flex-col leading-[1.25em]">
            <span class="text-sm font-medium">{{ poolLabels.get(row.id)?.pair }}</span>
            <span
              v-if="poolLabels.get(row.id)?.prefix"
              class="text-caption leading-4 text-rui-text-secondary"
            >
              {{ poolLabels.get(row.id)?.prefix }}
            </span>
          </div>
        </div>
      </template>
      <template #item.value="{ row }">
        <FiatDisplay :value="row.value" />
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
      <template
        v-if="balances.length > 1"
        #body.append
      >
        <RowAppend
          label-colspan="1"
          :label="t('common.total')"
          :right-patch-colspan="tableHeaders.length - 2"
          class-name="text-sm border-t border-default [&>td]:px-4 [&>td]:py-3"
        >
          <FiatDisplay
            :value="total"
            class="font-bold"
          />
        </RowAppend>
      </template>
    </RuiDataTable>
  </DashboardExpandableTable>
</template>
