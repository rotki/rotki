<script setup lang="ts">
import type { AssetBalance, AssetBalanceWithPrice, BigNumber, Nullable } from '@rotki/common';
import type { DataTableColumn, DataTableSortData } from '@rotki/ui-library';
import AmountDisplay from '@/components/display/amount/AmountDisplay.vue';
import PercentageDisplay from '@/components/display/PercentageDisplay.vue';
import EvmNativeTokenBreakdown from '@/components/EvmNativeTokenBreakdown.vue';
import AssetDetails from '@/components/helper/AssetDetails.vue';
import RowAppend from '@/components/helper/RowAppend.vue';
import { useAssetInfoRetrieval } from '@/composables/assets/retrieval';
import BalanceTopProtocols from '@/modules/balances/protocols/BalanceTopProtocols.vue';
import { TableId, useRememberTableSorting } from '@/modules/table/use-remember-table-sorting';
import { useGeneralSettingsStore } from '@/store/settings/general';
import { useStatisticsStore } from '@/store/statistics';
import { isEvmNativeToken } from '@/types/asset';
import { TableColumn } from '@/types/table-column';
import { assetFilterByKeyword } from '@/utils/assets';
import { sortAssetBalances } from '@/utils/balances';
import { bigNumberSum, calculatePercentage } from '@/utils/calculation';
import { some } from 'es-toolkit/compat';

defineOptions({
  name: 'AssetBalances',
});

const search = defineModel<string>('search', { default: '', required: false });

const props = withDefaults(
  defineProps<{
    balances: AssetBalanceWithPrice[];
    details?: {
      groupId?: string;
      chains?: string[];
    };
    loading?: boolean;
    hideTotal?: boolean;
    hideBreakdown?: boolean;
    stickyHeader?: boolean;
    isLiability?: boolean;
    allBreakdown?: boolean;
    visibleColumns?: TableColumn[];
    showPerProtocol?: boolean;
  }>(),
  {
    allBreakdown: false,
    details: undefined,
    hideBreakdown: false,
    hideTotal: false,
    isLiability: false,
    loading: false,
    showPerProtocol: false,
    stickyHeader: false,
    visibleColumns: () => [],
  },
);

const { t } = useI18n({ useScope: 'global' });

const { balances } = toRefs(props);
const expanded = ref<AssetBalanceWithPrice[]>([]);

const sort = ref<DataTableSortData<AssetBalanceWithPrice>>({
  column: 'usdValue',
  direction: 'desc' as const,
});

const { assetInfo, assetName, assetSymbol } = useAssetInfoRetrieval();
const { currencySymbol } = storeToRefs(useGeneralSettingsStore());
const statistics = useStatisticsStore();
const { totalNetWorthUsd } = storeToRefs(statistics);

const isExpanded = (asset: string) => some(get(expanded), { asset });

function expand(item: AssetBalanceWithPrice) {
  set(expanded, isExpanded(item.asset) ? [] : [item]);
}

function getAssets(item: AssetBalanceWithPrice): string[] {
  return item.breakdown?.map(entry => entry.asset) ?? [];
}

function assetFilter(item: Nullable<AssetBalance>) {
  return assetFilterByKeyword(item, get(search), assetName, assetSymbol);
}

const filteredBalances = computed(() => get(balances).filter(assetFilter));

const total = computed(() => bigNumberSum(get(filteredBalances).map(({ usdValue }) => usdValue)));

function percentageOfTotalNetValue(value: BigNumber) {
  return calculatePercentage(value, get(totalNetWorthUsd));
}

function percentageOfCurrentGroup(value: BigNumber) {
  return calculatePercentage(value, get(total));
}

const tableHeaders = computed<DataTableColumn<AssetBalanceWithPrice>[]>(() => {
  const headers: DataTableColumn<AssetBalanceWithPrice>[] = [{
    cellClass: 'py-0',
    class: 'text-no-wrap w-full',
    key: 'asset',
    label: t('common.asset'),
    sortable: true,
  }, {
    align: 'end',
    cellClass: 'py-0',
    key: 'usdPrice',
    label: t('common.price_in_symbol', {
      symbol: get(currencySymbol),
    }),
    sortable: true,
  }, {
    align: 'end',
    cellClass: 'py-0',
    key: 'amount',
    label: t('common.amount'),
    sortable: true,
  }, {
    align: 'end',
    cellClass: 'py-0',
    class: 'text-no-wrap',
    key: 'usdValue',
    label: t('common.value_in_symbol', {
      symbol: get(currencySymbol),
    }),
    sortable: true,
  }];

  if (props.showPerProtocol) {
    headers.splice(1, 0, {
      align: 'end',
      cellClass: 'py-0',
      class: 'text-no-wrap',
      key: 'perProtocol',
      label: t('common.protocol'),
      sortable: false,
    });
  }

  if (props.visibleColumns.includes(TableColumn.PERCENTAGE_OF_TOTAL_NET_VALUE)) {
    headers.push({
      align: 'end',
      cellClass: 'py-0',
      class: 'text-no-wrap',
      key: 'percentageOfTotalNetValue',
      label: t('dashboard_asset_table.headers.percentage_of_total_net_value'),
    });
  }

  if (props.visibleColumns.includes(TableColumn.PERCENTAGE_OF_TOTAL_CURRENT_GROUP)) {
    headers.push({
      align: 'end',
      cellClass: 'py-0',
      class: 'text-no-wrap',
      key: 'percentageOfTotalCurrentGroup',
      label: t('dashboard_asset_table.headers.percentage_of_total_current_group', {
        group: t('blockchain_balances.group_label'),
      }),
    });
  }

  return headers;
});

useRememberTableSorting<AssetBalanceWithPrice>(TableId.ASSET_BALANCES, sort, tableHeaders);

const sorted = computed<AssetBalanceWithPrice[]>(() => sortAssetBalances([...get(filteredBalances)], get(sort), assetInfo));
</script>

<template>
  <RuiDataTable
    v-model:sort.external="sort"
    :cols="tableHeaders"
    :rows="sorted"
    :loading="loading"
    :expanded="expanded"
    :loading-text="t('asset_balances.loading')"
    :empty="{ description: t('data_table.no_data') }"
    :sticky-header="stickyHeader"
    row-attr="asset"
    single-expand
    outlined
    dense
  >
    <template #item.asset="{ row }">
      <AssetDetails
        :asset="row.asset"
        :is-collection-parent="!!row.breakdown"
      />
    </template>
    <template #item.perProtocol="{ row }">
      <BalanceTopProtocols
        v-if="row.perProtocol"
        :protocols="row.perProtocol"
        :loading="!row.usdPrice || row.usdPrice.lt(0)"
        :asset="row.asset"
      />
    </template>
    <template #item.usdPrice="{ row }">
      <AmountDisplay
        :loading="!row.usdPrice || row.usdPrice.lt(0)"
        is-asset-price
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
    <template
      v-if="balances.length > 0 && !hideTotal"
      #body.append
    >
      <RowAppend
        label-colspan="3"
        :label="t('common.total')"
        :is-mobile="false"
        :right-patch-colspan="2"
        class-name="[&>td]:p-4 text-sm"
      >
        <AmountDisplay
          fiat-currency="USD"
          show-currency="symbol"
          :value="total"
        />
      </RowAppend>
    </template>
    <template #expanded-item="{ row }">
      <EvmNativeTokenBreakdown
        v-if="!hideBreakdown && isEvmNativeToken(row.asset)"
        :blockchain-only="!allBreakdown"
        :assets="getAssets(row)"
        :details="details"
        :identifier="row.asset"
        :is-liability="isLiability"
        class="bg-white dark:bg-[#1E1E1E] my-2"
      />
      <AssetBalances
        v-else
        v-bind="props"
        :visible-columns="[]"
        hide-total
        :balances="row.breakdown ?? []"
        :sticky-header="false"
        :is-liability="isLiability"
        :all-breakdown="allBreakdown"
        class="bg-white dark:bg-[#1E1E1E] my-2"
      />
    </template>
    <template #item.expand="{ row }">
      <RuiTableRowExpander
        v-if="row.breakdown || (!hideBreakdown && isEvmNativeToken(row.asset))"
        :expanded="isExpanded(row.asset)"
        @click="expand(row)"
      />
    </template>
  </RuiDataTable>
</template>
