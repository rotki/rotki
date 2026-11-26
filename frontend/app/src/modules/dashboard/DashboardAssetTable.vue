<script setup lang="ts">
import type { AssetBalanceWithPrice } from '@rotki/common';
import type { HTMLAttributes } from 'vue';
import { RuiDataTable, RuiIcon, RuiTableRowExpander, RuiTooltip } from '@rotki/ui-library';
import { useI18n } from 'vue-i18n';
import { AssetValueDisplay, FiatDisplay, ValueDisplay } from '@/modules/assets/amount-display/components';
import BalanceTopProtocols from '@/modules/balances/protocols/BalanceTopProtocols.vue';
import AssetRowDetails from '@/modules/balances/protocols/components/AssetRowDetails.vue';
import TableSearchField from '@/modules/core/table/TableSearchField.vue';
import DashboardAssetWarnings from '@/modules/dashboard/DashboardAssetWarnings.vue';
import DashboardExpandableTable from '@/modules/dashboard/DashboardExpandableTable.vue';
import { useDashboardAssetTable } from '@/modules/dashboard/use-dashboard-asset-table';
import VisibleColumnsSelector from '@/modules/dashboard/VisibleColumnsSelector.vue';
import { DashboardTableType } from '@/modules/settings/types/frontend-settings';
import PercentageDisplay from '@/modules/shell/components/display/PercentageDisplay.vue';
import RowAppend from '@/modules/shell/components/RowAppend.vue';

interface Props {
  title: string;
  balances: AssetBalanceWithPrice[];
  tableType: DashboardTableType;
  loading?: boolean;
  /** Add a column the page fills through the `comparison` slot, as the history view does. */
  showComparison?: boolean;
}

const { balances, loading = false, showComparison = false, tableType, title } = defineProps<Props & /* @vue-ignore */ Omit<HTMLAttributes, keyof Props>>();

defineSlots<{
  comparison: (props: { row: AssetBalanceWithPrice }) => unknown;
}>();

const { t } = useI18n({ useScope: 'global' });

const {
  emptyDescription,
  hidePagination,
  isAssetMissing,
  isPriceMissing,
  isRowExpandable,
  isValuePending,
  modelExpanded,
  modelSearch,
  modelSort,
  pagination,
  percentageOfCurrentGroup,
  percentageOfTotalNetValue,
  placeholderRowClass,
  redirectToManualBalance,
  searchable,
  setTablePagination,
  showTotal,
  sorted,
  tableHeaders,
  total,
  totalPending,
} = useDashboardAssetTable({
  balances: () => balances,
  showComparison: () => showComparison,
  tableType: () => tableType,
  title: () => title,
});
</script>

<template>
  <DashboardExpandableTable :count="balances.length">
    <template #title>
      {{ title }}
    </template>
    <template #details>
      <TableSearchField
        v-if="searchable"
        v-model="modelSearch"
      />

      <VisibleColumnsSelector
        :group="tableType"
        :group-label="title"
        size="sm"
      />
    </template>
    <template #shortDetails>
      <FiatDisplay
        :value="total"
        :loading="totalPending"
        class="text-h6 font-bold"
      />
    </template>
    <RuiDataTable
      v-model:sort.external="modelSort"
      data-testid="dashboard-asset-table-balances"
      :cols="tableHeaders"
      :rows="sorted"
      :item-class="placeholderRowClass"
      :loading="loading"
      :empty="{ description: emptyDescription }"
      :expanded="modelExpanded"
      :pagination="{
        page: pagination.page,
        limit: pagination.itemsPerPage,
        total: sorted.length,
      }"
      row-attr="asset"
      sticky-header
      single-expand
      dense
      :hide-pagination="hidePagination"
      class="rounded-t-none!"
      :class="{ 'border-t border-default': !hidePagination }"
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
        <RuiTooltip
          v-else-if="isPriceMissing(row.asset)"
          :open-delay="400"
          :class-names="{ tooltip: 'max-w-64' }"
        >
          <template #activator>
            <RuiIcon
              name="lu-banknote-x"
              size="16"
              class="text-rui-text-disabled cursor-help"
            />
          </template>
          {{ t('dashboard_asset_table.price_unknown') }}
        </RuiTooltip>
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
          :loading="isValuePending(row)"
        />
      </template>
      <template #item.comparison="{ row }">
        <slot
          name="comparison"
          :row="row"
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
        v-if="modelSearch.length > 0"
        #no-data
      >
        <span class="text-rui-text-secondary">
          {{ t('dashboard_asset_table.no_search_result', { search: modelSearch }) }}
        </span>
      </template>
      <template
        v-if="showTotal"
        #body.append
      >
        <RowAppend
          label-colspan="4"
          :label="t('common.total')"
          :right-patch-colspan="tableHeaders.length - 4"
          variant="bordered"
          data-testid="dashboard-asset-table-total"
        >
          <FiatDisplay
            :value="total"
            :loading="totalPending"
            class="font-bold"
          />
        </RowAppend>
      </template>
      <template #expanded-item="{ row }">
        <AssetRowDetails
          :row="row"
          :breakdown="{ isLiability: tableType === DashboardTableType.LIABILITIES }"
          :loading="loading"
        />
      </template>
      <template #item.expand="{ row }">
        <RuiTableRowExpander
          v-if="isRowExpandable(row)"
          :expanded="modelExpanded.includes(row)"
          @click="modelExpanded = modelExpanded.includes(row) ? [] : [row]"
        />
      </template>
    </RuiDataTable>
  </DashboardExpandableTable>
</template>
