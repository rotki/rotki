<script setup lang="ts">
import type { AssetBalanceWithPrice } from '@rotki/common';
import { AssetValueDisplay, FiatDisplay, ValueDisplay } from '@/modules/assets/amount-display/components';
import BalanceTopProtocols from '@/modules/balances/protocols/BalanceTopProtocols.vue';
import AssetRowDetails from '@/modules/balances/protocols/components/AssetRowDetails.vue';
import DashboardAssetWarnings from '@/modules/dashboard/DashboardAssetWarnings.vue';
import DashboardExpandableTable from '@/modules/dashboard/DashboardExpandableTable.vue';
import { useDashboardAssetData } from '@/modules/dashboard/use-dashboard-asset-data';
import { useDashboardAssetOperations } from '@/modules/dashboard/use-dashboard-asset-operations';
import { useDashboardStores } from '@/modules/dashboard/use-dashboard-stores';
import { useDashboardTableConfig } from '@/modules/dashboard/use-dashboard-table-config';
import VisibleColumnsSelector from '@/modules/dashboard/VisibleColumnsSelector.vue';
import { DashboardTableType } from '@/modules/settings/types/frontend-settings';
import PercentageDisplay from '@/modules/shell/components/display/PercentageDisplay.vue';
import RowAppend from '@/modules/shell/components/RowAppend.vue';

const { balances, loading = false, tableType, title } = defineProps<{
  title: string;
  balances: AssetBalanceWithPrice[];
  tableType: DashboardTableType;
  loading?: boolean;
}>();

const { t } = useI18n({ useScope: 'global' });

// Stores
const { totalNetWorth } = useDashboardStores();

// Use composables - sort needs to be defined first for the computed dependency
const { pagination, setPage, setTablePagination, sort, tableHeaders } = useDashboardTableConfig(
  () => tableType,
  () => title,
  totalNetWorth,
);

const {
  isAssetMissing,
  percentageOfCurrentGroup,
  percentageOfTotalNetValue,
  search,
  sorted,
  total,
} = useDashboardAssetData(() => balances, sort);

const { expanded, isRowExpandable, redirectToManualBalance } = useDashboardAssetOperations(() => tableType);

// Watch search to reset pagination
watch(search, () => setPage(1));
</script>

<template>
  <DashboardExpandableTable>
    <template #title>
      {{ title }}
    </template>
    <template #details>
      <RuiTextField
        v-model="search"
        variant="outlined"
        color="primary"
        dense
        prepend-icon="lu-search"
        :label="t('common.actions.search')"
        class="max-w-[28rem] w-full"
        hide-details
        clearable
        @click:clear="search = ''"
      />

      <VisibleColumnsSelector
        :group="tableType"
        :group-label="title"
      />
    </template>
    <template #shortDetails>
      <FiatDisplay
        :value="total"
        class="text-h6 font-bold"
      />
    </template>
    <RuiDataTable
      v-model:sort.external="sort"
      data-cy="dashboard-asset-table__balances"
      :cols="tableHeaders"
      :rows="sorted"
      :loading="loading"
      :empty="{ description: t('data_table.no_data') }"
      :expanded="expanded"
      :pagination="{
        page: pagination.page,
        limit: pagination.itemsPerPage,
        total: sorted.length,
      }"
      row-attr="asset"
      sticky-header
      single-expand
      outlined
      dense
      @update:pagination="setTablePagination($event)"
    >
      <template #item.asset="{ row }">
        <DashboardAssetWarnings
          :asset="row"
          :is-asset-missing="isAssetMissing(row)"
          @missing-asset-click="redirectToManualBalance($event)"
        />
      </template>
      <template #item.protocol="{ row }">
        <BalanceTopProtocols
          v-if="row.perProtocol"
          :protocols="row.perProtocol"
          :loading="!row.price || row.price.lt(0)"
          :asset="row.asset"
        />
      </template>
      <template #item.price="{ row }">
        <template v-if="isAssetMissing(row)">
          -
        </template>
        <FiatDisplay
          v-else
          :price-asset="row.asset"
          :value="row.price"
          :loading="!row.price || row.price.lt(0)"
        />
      </template>
      <template #item.amount="{ row }">
        <ValueDisplay :value="row.amount" />
      </template>
      <template #item.value="{ row }">
        <AssetValueDisplay
          :asset="row.asset"
          :amount="row.amount"
          :price="row.price"
          :value="row.value"
        />
      </template>
      <template #item.percentageOfTotalNetValue="{ row }">
        <PercentageDisplay
          :value="percentageOfTotalNetValue(row)"
          :asset-padding="0.1"
        />
      </template>
      <template #item.percentageOfTotalCurrentGroup="{ row }">
        <PercentageDisplay
          :value="percentageOfCurrentGroup(row)"
          :asset-padding="0.1"
        />
      </template>
      <template
        v-if="search.length > 0"
        #no-data
      >
        <span class="text-rui-text-secondary">
          {{ t('dashboard_asset_table.no_search_result', { search }) }}
        </span>
      </template>
      <template
        v-if="balances.length > 0 && (!search || search.length === 0)"
        #body.append
      >
        <RowAppend
          label-colspan="4"
          :label="t('common.total')"
          :right-patch-colspan="tableHeaders.length - 4"
          class-name="text-sm [&_td]:p-4"
        >
          <FiatDisplay :value="total" />
        </RowAppend>
      </template>
      <template #expanded-item="{ row }">
        <AssetRowDetails
          :row="row"
          :is-liability="tableType === DashboardTableType.LIABILITIES"
          :loading="loading"
        />
      </template>
      <template #item.expand="{ row }">
        <RuiTableRowExpander
          v-if="isRowExpandable(row)"
          :expanded="expanded.includes(row)"
          @click="expanded = expanded.includes(row) ? [] : [row]"
        />
      </template>
    </RuiDataTable>
  </DashboardExpandableTable>
</template>
