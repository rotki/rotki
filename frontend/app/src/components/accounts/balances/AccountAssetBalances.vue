<script setup lang="ts">
import type { AssetBalance } from '@rotki/common';
import type {
  DataTableColumn,
  DataTableSortData,
} from '@rotki/ui-library-compat';

const props = defineProps<{ assets: AssetBalance[]; title: string }>();

const { t } = useI18n();
const { assets } = toRefs(props);

const { assetPrice } = useBalancePricesStore();
const { currencySymbol } = storeToRefs(useGeneralSettingsStore());
const { assetInfo } = useAssetInfoRetrieval();

const sort: Ref<DataTableSortData> = ref({
  column: 'usdValue',
  direction: 'desc' as const,
});

const assetsWithPrice = computed(() =>
  get(assets).map(row => ({ ...row, price: get(getPrice(row.asset)) })),
);

const sortItems = getSortItems(asset => get(assetInfo(asset)));

const sorted = computed(() => {
  const sortBy = get(sort);
  const data = [...get(assetsWithPrice)];
  if (!Array.isArray(sortBy) && sortBy?.column) {
    return sortItems(
      data,
      [sortBy.column as keyof AssetBalance],
      [sortBy.direction === 'desc'],
    );
  }
  return data;
});

const headers = computed<DataTableColumn[]>(() => [
  {
    label: t('common.asset').toString(),
    class: 'text-no-wrap w-full',
    cellClass: 'py-1',
    key: 'asset',
    sortable: true,
  },
  {
    label: t('common.price_in_symbol', {
      symbol: get(currencySymbol),
    }).toString(),
    class: 'text-no-wrap',
    cellClass: 'py-1',
    align: 'end',
    key: 'price',
    sortable: true,
  },
  {
    label: t('common.amount').toString(),
    key: 'amount',
    class: 'text-no-wrap',
    cellClass: 'py-1',
    align: 'end',
    sortable: true,
  },
  {
    label: t('common.value_in_symbol', {
      symbol: get(currencySymbol),
    }).toString(),
    key: 'usdValue',
    align: 'end',
    class: 'text-no-wrap',
    cellClass: 'py-1',
    sortable: true,
  },
]);

const getPrice = (asset: string) => get(assetPrice(asset)) ?? Zero;
</script>

<template>
  <RuiCard>
    <template #header>
      {{ title }}
    </template>
    <RuiDataTable
      :rows="sorted"
      :cols="headers"
      :sort.sync="sort"
      :sort-modifiers="{ external: true }"
      :empty="{ description: t('data_table.no_data') }"
      row-attr="asset"
      outlined
    >
      <template #item.asset="{ row }">
        <AssetDetails
          opens-details
          :asset="row.asset"
        />
      </template>
      <template #item.price="{ row }">
        <AmountDisplay
          v-if="assetPrice(row.asset).value"
          tooltip
          show-currency="symbol"
          fiat-currency="USD"
          :price-asset="row.asset"
          :value="getPrice(row.asset)"
        />
        <div v-else>
          -
        </div>
      </template>
      <template #item.amount="{ row }">
        <AmountDisplay :value="row.amount" />
      </template>
      <template #item.usdValue="{ row }">
        <AmountDisplay
          fiat-currency="USD"
          :value="row.usdValue"
          show-currency="symbol"
        />
      </template>
    </RuiDataTable>
  </RuiCard>
</template>
