<script setup lang="ts">
import { TableColumn } from '@/types/table-column';
import { isEvmNativeToken } from '@/types/asset';
import { DashboardTableType } from '@/types/settings/frontend-settings';
import type { BigNumber, Nullable } from '@rotki/common';
import type { DataTableColumn, DataTableSortData, TablePaginationData } from '@rotki/ui-library';
import type { AssetBalanceWithBreakdown } from '@/types/balances';

const props = withDefaults(defineProps<{
  title: string;
  balances: AssetBalanceWithBreakdown[];
  tableType: DashboardTableType;
  loading?: boolean;
}>(), { loading: false });

const { t } = useI18n();

const { balances, title, tableType } = toRefs(props);
const search = ref('');

const expanded = ref<AssetBalanceWithBreakdown[]>([]);

const sort = ref<DataTableSortData<AssetBalanceWithBreakdown>>({
  column: 'value',
  direction: 'desc' as const,
});

const pagination = ref({
  page: 1,
  itemsPerPage: 10,
});

const { currencySymbol } = storeToRefs(useGeneralSettingsStore());
const { assetSymbol, assetName, assetInfo } = useAssetInfoRetrieval();
const { dashboardTablesVisibleColumns } = storeToRefs(useFrontendSettingsStore());
const statisticsStore = useStatisticsStore();
const { totalNetWorthUsd } = storeToRefs(statisticsStore);

const total = computed(() => sum(get(balances)));

function assetFilter(item: Nullable<AssetBalanceWithBreakdown>) {
  return assetFilterByKeyword(item, get(search), assetName, assetSymbol);
}

function percentageOfTotalNetValue(value: BigNumber) {
  const netWorth = get(totalNetWorthUsd) as BigNumber;
  const totalValue = netWorth.lt(0) ? get(total) : netWorth;
  return calculatePercentage(value, totalValue);
}

function percentageOfCurrentGroup(value: BigNumber) {
  return calculatePercentage(value, get(total));
}

function setPage(page: number) {
  set(pagination, {
    ...get(pagination),
    page,
  });
}

function setTablePagination(event: TablePaginationData | undefined) {
  if (!isDefined(event))
    return;

  const { page, limit } = event;
  set(pagination, {
    page,
    itemsPerPage: limit,
  });
}

function getAssets(item: AssetBalanceWithBreakdown): string[] {
  return item.breakdown?.map(entry => entry.asset) ?? [];
}

const sorted = computed<AssetBalanceWithBreakdown[]>(() => {
  const filteredBalances = get(balances).filter(assetFilter);
  return sortAssetBalances(filteredBalances, get(sort), assetInfo);
});

const cols = computed<DataTableColumn<AssetBalanceWithBreakdown>[]>(() => {
  const visibleColumns = get(dashboardTablesVisibleColumns)[get(tableType)];

  const headers: DataTableColumn<AssetBalanceWithBreakdown>[] = [
    {
      label: t('common.asset'),
      key: 'asset',
      class: 'text-no-wrap w-full',
      cellClass: 'py-0',
      sortable: true,
    },
    {
      label: t('common.price_in_symbol', {
        symbol: get(currencySymbol),
      }),
      key: 'price',
      align: 'end',
      class: 'text-no-wrap',
      cellClass: 'py-0',
      sortable: true,
    },
    {
      label: t('common.amount'),
      key: 'amount',
      align: 'end',
      cellClass: 'py-0',
      sortable: true,
    },
    {
      label: t('common.value_in_symbol', {
        symbol: get(currencySymbol),
      }),
      key: 'value',
      align: 'end',
      class: 'text-no-wrap',
      cellClass: 'py-0',
      sortable: true,
    },
  ];

  if (visibleColumns.includes(TableColumn.PERCENTAGE_OF_TOTAL_NET_VALUE)) {
    headers.push({
      label: get(totalNetWorthUsd).gt(0)
        ? t('dashboard_asset_table.headers.percentage_of_total_net_value')
        : t('dashboard_asset_table.headers.percentage_total'),
      key: 'percentageOfTotalNetValue',
      align: 'end',
      cellClass: 'py-0',
      class: 'text-no-wrap',
    });
  }

  if (visibleColumns.includes(TableColumn.PERCENTAGE_OF_TOTAL_CURRENT_GROUP)) {
    headers.push({
      label: t('dashboard_asset_table.headers.percentage_of_total_current_group', {
        group: get(title),
      }),
      key: 'percentageOfTotalCurrentGroup',
      align: 'end',
      cellClass: 'py-0',
      class: 'text-no-wrap',
    });
  }

  return headers;
});

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
        prepend-icon="search-line"
        :label="t('common.actions.search')"
        :class="$style['dashboard-asset-table__search']"
        hide-details
        clearable
        @click:clear="search = ''"
      />
      <RuiMenu
        id="dashboard-asset-table__column-filter"
        menu-class="max-w-[15rem]"
        :popper="{ placement: 'bottom-end' }"
      >
        <template #activator="{ attrs }">
          <MenuTooltipButton
            :tooltip="t('dashboard_asset_table.select_visible_columns')"
            class-name="dashboard-asset-table__column-filter__button"
            custom-color
            v-bind="attrs"
          >
            <RuiIcon name="more-2-fill" />
          </MenuTooltipButton>
        </template>
        <VisibleColumnsSelector
          :group="tableType"
          :group-label="title"
        />
      </RuiMenu>
    </template>
    <template #shortDetails>
      <AmountDisplay
        :fiat-currency="currencySymbol"
        :value="total"
        show-currency="symbol"
        class="text-h6 font-bold"
      />
    </template>
    <RuiDataTable
      v-model:sort.external="sort"
      data-cy="dashboard-asset-table__balances"
      :cols="cols"
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
        <AssetDetails
          opens-details
          :asset="row.asset"
          :is-collection-parent="!!row.breakdown"
        />
      </template>
      <template #item.price="{ row }">
        <AmountDisplay
          :loading="!row.price || row.price.lt(0)"
          no-scramble
          show-currency="symbol"
          :price-asset="row.asset"
          :price-of-asset="row.price"
          :value="row.price"
        />
      </template>
      <template #item.amount="{ row }">
        <AmountDisplay :value="row.amount" />
      </template>
      <template #item.value="{ row }">
        <AmountDisplay
          show-currency="symbol"
          :loading="row.price.lt(0)"
          :fiat-currency="currencySymbol"
          :value="row.value"
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
          label-colspan="3"
          :label="t('common.total')"
          :right-patch-colspan="cols.length - 4"
          :class-name="$style['dashboard-asset-table__body-append']"
        >
          <AmountDisplay
            :fiat-currency="currencySymbol"
            :value="total"
            :loading="loading || (total.eq(0) && balances.length > 0)"
            show-currency="symbol"
          />
        </RowAppend>
      </template>
      <template #expanded-item="{ row }">
        <EvmNativeTokenBreakdown
          v-if="isEvmNativeToken(row.asset)"
          show-percentage
          :total="row.value"
          :assets="getAssets(row)"
          :identifier="row.asset"
          :is-liability="tableType === DashboardTableType.LIABILITIES"
          class="bg-white dark:bg-[#1E1E1E] my-2"
        />
        <AssetBalances
          v-else
          hide-total
          v-bind="props"
          :balances="row.breakdown ?? []"
          all-breakdown
          :is-liability="tableType === DashboardTableType.LIABILITIES"
          class="bg-white dark:bg-[#1E1E1E] my-2"
        />
      </template>
      <template #item.expand="{ row }">
        <RuiTableRowExpander
          v-if="row.breakdown || isEvmNativeToken(row.asset)"
          :expanded="expanded.includes(row)"
          @click="expanded = expanded.includes(row) ? [] : [row]"
        />
      </template>
    </RuiDataTable>
  </DashboardExpandableTable>
</template>

<style module lang="scss">
.dashboard-asset-table {
  &__search {
    @apply max-w-[28rem] w-full;
  }

  &__body-append {
    @apply text-sm;

    td {
      @apply p-4;
    }
  }
}
</style>
