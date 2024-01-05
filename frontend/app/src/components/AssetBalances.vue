<script setup lang="ts">
import { type AssetBalance, type AssetBalanceWithPrice } from '@rotki/common';
import {
  type DataTableColumn,
  type DataTableSortData
} from '@rotki/ui-library-compat';
import { type Ref } from 'vue';
import { some } from 'lodash-es';
import { isEvmNativeToken } from '@/types/asset';

defineOptions({
  name: 'AssetBalances'
});

const props = withDefaults(
  defineProps<{
    balances: AssetBalanceWithPrice[];
    loading?: boolean;
    hideTotal?: boolean;
    hideBreakdown?: boolean;
    stickyHeader?: boolean;
  }>(),
  {
    loading: false,
    hideTotal: false,
    hideBreakdown: false,
    stickyHeader: false
  }
);

const { t } = useI18n();

const { balances } = toRefs(props);
const expanded: Ref<AssetBalanceWithPrice[]> = ref([]);

const total = computed(() =>
  bigNumberSum(balances.value.map(({ usdValue }) => usdValue))
);

const { currencySymbol } = storeToRefs(useGeneralSettingsStore());
const { assetInfo } = useAssetInfoRetrieval();

const sort: Ref<DataTableSortData> = ref({
  column: 'usdValue',
  direction: 'desc' as const
});

const tableHeaders = computed<DataTableColumn[]>(() => [
  {
    label: t('common.asset'),
    key: 'asset',
    class: 'text-no-wrap w-full',
    cellClass: 'py-0',
    sortable: true
  },
  {
    label: t('common.price_in_symbol', {
      symbol: get(currencySymbol)
    }),
    key: 'usdPrice',
    align: 'end',
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
]);

const sortItems = getSortItems(asset => get(assetInfo(asset)));

const sorted = computed(() => {
  const sortBy = get(sort);
  const data = [...get(balances)];
  if (!Array.isArray(sortBy) && sortBy?.column) {
    return sortItems(
      data,
      [sortBy.column as keyof AssetBalance],
      [sortBy.direction === 'desc']
    );
  }
  return data;
});

const isExpanded = (asset: string) => some(get(expanded), { asset });

const expand = (item: AssetBalanceWithPrice) => {
  set(expanded, isExpanded(item.asset) ? [] : [item]);
};
</script>

<template>
  <RuiDataTable
    :cols="tableHeaders"
    :rows="sorted"
    :loading="loading"
    :expanded="expanded"
    :loading-text="t('asset_balances.loading')"
    :sort.sync="sort"
    :sort-modifiers="{ external: true }"
    :empty="{ description: t('data_table.no_data') }"
    :sticky-offset="64"
    :sticky-header="stickyHeader"
    row-attr="asset"
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
    <template v-if="balances.length > 0 && !hideTotal" #body.append>
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
        blockchain-only
        :identifier="row.asset"
        class="bg-white dark:bg-[#1E1E1E]"
      />
      <AssetBalances
        v-else
        v-bind="props"
        hide-total
        :balances="row.breakdown ?? []"
        :sticky-header="false"
        class="bg-white dark:bg-[#1E1E1E]"
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
