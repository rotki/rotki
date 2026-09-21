<script setup lang="ts">
import type { AssetBalanceWithPrice } from '@rotki/common';
import { AssetValueDisplay, FiatDisplay, ValueDisplay } from '@/modules/assets/amount-display/components';
import BalanceTopProtocols from '@/modules/balances/protocols/BalanceTopProtocols.vue';
import AssetRowDetails from '@/modules/balances/protocols/components/AssetRowDetails.vue';
import { useBalancePricesStore } from '@/modules/balances/use-balance-prices-store';
import { useValuePending } from '@/modules/balances/value-pending';
import DashboardAssetWarnings from '@/modules/dashboard/DashboardAssetWarnings.vue';
import DashboardExpandableTable from '@/modules/dashboard/DashboardExpandableTable.vue';
import { useDashboardAssetData } from '@/modules/dashboard/use-dashboard-asset-data';
import { useDashboardAssetOperations } from '@/modules/dashboard/use-dashboard-asset-operations';
import { useDashboardStores } from '@/modules/dashboard/use-dashboard-stores';
import { useDashboardTableConfig } from '@/modules/dashboard/use-dashboard-table-config';
import VisibleColumnsSelector from '@/modules/dashboard/VisibleColumnsSelector.vue';
import { fitsEveryLimit } from '@/modules/session/use-items-per-page';
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

const { totalNetWorth } = useDashboardStores();
const { prices } = storeToRefs(useBalancePricesStore());
const { isTotalPending, isValuePending } = useValuePending();

// Use composables - sort needs to be defined first for the computed dependency
const { modelSort, pagination, setPage, setTablePagination, tableHeaders } = useDashboardTableConfig(
  () => tableType,
  () => title,
  totalNetWorth,
);

const {
  isAssetMissing,
  percentageOfCurrentGroup,
  percentageOfTotalNetValue,
  modelSearch,
  sorted,
  total,
} = useDashboardAssetData(() => balances, modelSort);

const { isRowExpandable, modelExpanded, redirectToManualBalance } = useDashboardAssetOperations(() => tableType);

const emptyDescription = computed<string>(() => tableType === DashboardTableType.ASSETS
  ? t('dashboard_asset_table.no_assets')
  : t('data_table.no_data'));

function isPriceMissing(asset: string): boolean {
  return get(prices)[asset]?.priceMissing === true;
}

/** Below this many rows the whole table is in view, so a search field only takes space. */
const SEARCH_MIN_ROWS = 11;

const totalPending = computed<boolean>(() => isTotalPending(get(sorted)));

const searchable = computed<boolean>(() => balances.length >= SEARCH_MIN_ROWS);

const hidePagination = computed<boolean>(() => fitsEveryLimit(get(sorted).length));

/** With one row the row is its own total. */
const showTotal = computed<boolean>(() => get(sorted).length > 1 && get(modelSearch).length === 0);

watch(modelSearch, () => setPage(1));
</script>

<template>
  <DashboardExpandableTable :count="balances.length">
    <template #title>
      {{ title }}
    </template>
    <template #details>
      <RuiTextField
        v-if="searchable"
        v-model="modelSearch"
        variant="outlined"
        color="primary"
        dense
        prepend-icon="lu-search"
        :placeholder="t('common.actions.search')"
        :aria-label="t('common.actions.search')"
        class="max-w-[16rem] w-full [&_input]:!py-1.5 [&_input]:!text-sm [&_input]:!leading-5 [&_input::placeholder]:!opacity-100 [&_input::placeholder]:!text-rui-text-secondary [&_svg]:!size-4"
        hide-details
        clearable
        @click:clear="modelSearch = ''"
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
      :hide-default-header="hidePagination"
      :hide-default-footer="hidePagination"
      class="!rounded-t-none"
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
          :class-names="{ tooltip: 'max-w-[16rem]' }"
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
          class-name="text-sm border-t border-default [&_td]:px-4 [&_td]:py-3"
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
