<script setup lang="ts">
import {
  type AssetBalance,
  type AssetBalanceWithPrice,
  type BigNumber
} from '@rotki/common';
import {
  type DataTableColumn,
  type DataTableSortColumn
} from '@rotki/ui-library-compat';
import { type Ref } from 'vue';
import { type Nullable } from '@/types';
import { CURRENCY_USD } from '@/types/currencies';
import { type DashboardTableType } from '@/types/settings/frontend-settings';
import { TableColumn } from '@/types/table-column';
import { isEvmNativeToken } from '@/types/asset';

const props = withDefaults(
  defineProps<{
    title: string;
    balances: AssetBalanceWithPrice[];
    tableType: DashboardTableType;
    loading?: boolean;
  }>(),
  { loading: false }
);

const { t } = useI18n();
const css = useCssModule();

const { balances, title, tableType } = toRefs(props);
const search = ref('');

const expanded: Ref<AssetBalanceWithPrice[]> = ref([]);

const sort: Ref<DataTableSortColumn | DataTableSortColumn[] | undefined> = ref({
  column: 'usdValue',
  direction: 'desc' as const
});

const { currencySymbol } = storeToRefs(useGeneralSettingsStore());

const { exchangeRate } = useBalancePricesStore();
const totalInUsd = computed(() =>
  aggregateTotal(get(balances), CURRENCY_USD, One)
);
const total = computed(() => {
  const mainCurrency = get(currencySymbol);
  return get(totalInUsd).multipliedBy(get(exchangeRate(mainCurrency)) ?? One);
});

const { assetSymbol, assetName, assetInfo } = useAssetInfoRetrieval();

const assetFilter = (item: Nullable<AssetBalance>) => {
  const keyword = get(search).toLocaleLowerCase()?.trim() ?? '';
  if (!keyword || !item) {
    return true;
  }
  const name = get(assetName(item.asset))?.toLocaleLowerCase()?.trim();
  const symbol = get(assetSymbol(item.asset))?.toLocaleLowerCase()?.trim();
  return symbol.includes(keyword) || name.includes(keyword);
};

const statisticsStore = useStatisticsStore();
const { totalNetWorthUsd } = storeToRefs(statisticsStore);
const percentageOfTotalNetValue = (value: BigNumber) => {
  const netWorth = get(totalNetWorthUsd) as BigNumber;
  const total = netWorth.lt(0) ? get(totalInUsd) : netWorth;
  return calculatePercentage(value, total);
};

const percentageOfCurrentGroup = (value: BigNumber) =>
  calculatePercentage(value, get(totalInUsd));

const { dashboardTablesVisibleColumns } = storeToRefs(
  useFrontendSettingsStore()
);

const sortItems = getSortItems(asset => get(assetInfo(asset)));

const filtered = computed(() => {
  const sortBy = get(sort);
  const data = get(balances).filter(assetFilter);
  if (!Array.isArray(sortBy) && sortBy?.column) {
    return sortItems(
      data,
      [sortBy.column as keyof AssetBalance],
      [sortBy.direction === 'desc']
    );
  }
  return data;
});

const tableHeaders = computed<DataTableColumn[]>(() => {
  const visibleColumns = get(dashboardTablesVisibleColumns)[get(tableType)];

  const headers: DataTableColumn[] = [
    {
      label: t('common.asset'),
      key: 'asset',
      class: 'text-no-wrap',
      cellClass: 'py-0',
      sortable: true
    },
    {
      label: t('common.price_in_symbol', {
        symbol: get(currencySymbol)
      }),
      key: 'usdPrice',
      align: 'end',
      class: 'text-no-wrap',
      cellClass: 'py-0',
      sortable: true
    },
    {
      label: t('common.amount'),
      key: 'amount',
      align: 'end',
      cellClass: 'py-0',
      sortable: true
    },
    {
      label: t('common.value_in_symbol', {
        symbol: get(currencySymbol)
      }),
      key: 'usdValue',
      align: 'end',
      class: 'text-no-wrap',
      cellClass: 'py-0',
      sortable: true
    }
  ];

  if (visibleColumns.includes(TableColumn.PERCENTAGE_OF_TOTAL_NET_VALUE)) {
    headers.push({
      label: get(totalNetWorthUsd).gt(0)
        ? t('dashboard_asset_table.headers.percentage_of_total_net_value')
        : t('dashboard_asset_table.headers.percentage_total'),
      key: 'percentageOfTotalNetValue',
      align: 'end',
      cellClass: 'py-0',
      class: 'text-no-wrap'
    });
  }

  if (visibleColumns.includes(TableColumn.PERCENTAGE_OF_TOTAL_CURRENT_GROUP)) {
    headers.push({
      label: t(
        'dashboard_asset_table.headers.percentage_of_total_current_group',
        {
          group: get(title)
        }
      ),
      key: 'percentageOfTotalCurrentGroup',
      align: 'end',
      cellClass: 'py-0',
      class: 'text-no-wrap'
    });
  }

  return headers;
});
</script>

<template>
  <DashboardExpandableTable>
    <template #title>{{ title }}</template>
    <template #details>
      <RuiTextField
        v-model="search"
        variant="outlined"
        color="primary"
        dense
        prepend-icon="search-line"
        :label="t('common.actions.search')"
        :class="css['dashboard-asset-table__search']"
        hide-details
        clearable
        @click:clear="search = ''"
      />
      <VMenu
        id="dashboard-asset-table__column-filter"
        transition="slide-y-transition"
        max-width="250px"
        nudge-bottom="20"
        offset-y
        left
      >
        <template #activator="{ on }">
          <MenuTooltipButton
            :tooltip="t('dashboard_asset_table.select_visible_columns')"
            class-name="dashboard-asset-table__column-filter__button"
            v-on="on"
          >
            <RuiIcon name="more-2-fill" />
          </MenuTooltipButton>
        </template>
        <VisibleColumnsSelector :group="tableType" :group-label="title" />
      </VMenu>
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
      data-cy="dashboard-asset-table__balances"
      :cols="tableHeaders"
      :rows="filtered"
      :loading="loading"
      :sort.sync="sort"
      :sort-modifiers="{ external: true }"
      :empty="{ description: t('data_table.no_data') }"
      :expanded="expanded"
      :sticky-offset="64"
      row-attr="asset"
      sticky-header
      single-expand
      outlined
    >
      <template #item.asset="{ row }">
        <AssetDetails
          opens-details
          :asset="row.asset"
          :is-collection-parent="!!row.breakdown"
        />
      </template>
      <template #item.usdPrice="{ row }">
        <AmountDisplay
          :loading="!row.usdPrice || row.usdPrice.lt(0)"
          no-scramble
          show-currency="symbol"
          :price-asset="row.asset"
          :price-of-asset="row.usdPrice"
          fiat-currency="USD"
          :value="row.usdPrice"
        />
      </template>
      <template #item.amount="{ row }">
        <AmountDisplay :value="row.amount" />
      </template>
      <template #item.usdValue="{ row }">
        <AmountDisplay
          show-currency="symbol"
          :amount="row.amount"
          :price-asset="row.asset"
          :price-of-asset="row.usdPrice"
          fiat-currency="USD"
          :value="row.usdValue"
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
      <template #no-results>
        <span class="text-rui-text-secondary">
          {{
            t('dashboard_asset_table.no_search_result', {
              search
            })
          }}
        </span>
      </template>
      <template
        v-if="balances.length > 0 && (!search || search.length === 0)"
        #body.append
      >
        <RowAppend
          label-colspan="3"
          :label="t('common.total')"
          :right-patch-colspan="tableHeaders.length - 4"
          :class-name="css['dashboard-asset-table__body-append']"
        >
          <AmountDisplay
            :fiat-currency="currencySymbol"
            :value="total"
            show-currency="symbol"
          />
        </RowAppend>
      </template>
      <template #expanded-item="{ row }">
        <EvmNativeTokenBreakdown
          v-if="isEvmNativeToken(row.asset)"
          show-percentage
          :total="row.usdValue"
          :identifier="row.asset"
          class="bg-white dark:bg-[#1E1E1E]"
        />
        <AssetBalances
          v-else
          hide-total
          v-bind="props"
          :balances="row.breakdown ?? []"
          class="bg-white dark:bg-[#1E1E1E]"
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
