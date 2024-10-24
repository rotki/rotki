<script setup lang="ts">
import type { DataTableColumn, DataTableSortData } from '@rotki/ui-library';
import type { AssetBalance, AssetBalanceWithPrice } from '@/types/balances';

const props = withDefaults(
  defineProps<{
    assets: AssetBalance[];
    title: string;
    flat?: boolean;
  }>(),
  {
    flat: false,
  },
);

const { t } = useI18n();
const { assets } = toRefs(props);

const { assetPrice } = useBalancePricesStore();
const { currencySymbol } = storeToRefs(useGeneralSettingsStore());
const { assetInfo } = useAssetInfoRetrieval();
const getPrice = (asset: string) => get(assetPrice(asset)) ?? Zero;

const sort = ref<DataTableSortData<AssetBalanceWithPrice>>({
  column: 'value',
  direction: 'desc' as const,
});

const assetsWithPrice = computed<AssetBalanceWithPrice[]>(() =>
  get(assets).map(row => ({ ...row, price: get(getPrice(row.asset)) })),
);

const sortItems = getSortItems<AssetBalanceWithPrice>(asset => get(assetInfo(asset)));

const sorted = computed<AssetBalanceWithPrice[]>(() => {
  const sortBy = get(sort);
  const data = [...get(assetsWithPrice)];
  if (!Array.isArray(sortBy) && sortBy?.column)
    return sortItems(data, [sortBy.column as keyof AssetBalance], [sortBy.direction === 'desc']);

  return data;
});

const headers = computed<DataTableColumn<AssetBalanceWithPrice>[]>(() => [
  {
    label: t('common.asset'),
    class: 'text-no-wrap w-full',
    cellClass: 'py-1',
    key: 'asset',
    sortable: true,
  },
  {
    label: t('common.price_in_symbol', {
      symbol: get(currencySymbol),
    }),
    class: 'text-no-wrap',
    cellClass: 'py-1',
    align: 'end',
    key: 'price',
    sortable: true,
  },
  {
    label: t('common.amount'),
    key: 'amount',
    class: 'text-no-wrap',
    cellClass: 'py-1',
    align: 'end',
    sortable: true,
  },
  {
    label: t('common.value_in_symbol', {
      symbol: get(currencySymbol),
    }),
    key: 'value',
    align: 'end',
    class: 'text-no-wrap',
    cellClass: 'py-1',
    sortable: true,
  },
]);
</script>

<template>
  <RuiCard
    :no-padding="flat"
    :variant="flat ? 'flat' : 'outlined'"
    class="!rounded-xl my-2"
  >
    <template
      v-if="!flat && title"
      #header
    >
      {{ title }}
    </template>
    <RuiDataTable
      v-model:sort.external="sort"
      :rows="sorted"
      :cols="headers"
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
          no-scramble
          show-currency="symbol"
          fiat-currency="USD"
          :price-asset="row.asset"
          :price-of-asset="row.price"
          :value="getPrice(row.asset)"
        />
        <div v-else>
          -
        </div>
      </template>
      <template #item.amount="{ row }">
        <AmountDisplay :value="row.amount" />
      </template>
      <template #item.value="{ row }">
        <AmountDisplay
          :fiat-currency="currencySymbol"
          :value="row.value"
          show-currency="symbol"
        />
      </template>
    </RuiDataTable>
  </RuiCard>
</template>
