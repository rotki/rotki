<script setup lang="ts">
import type { DataTableColumn, DataTableSortData } from '@rotki/ui-library';
import AmountDisplay from '@/components/display/amount/AmountDisplay.vue';
import AssetDetails from '@/components/helper/AssetDetails.vue';
import RowAppend from '@/components/helper/RowAppend.vue';
import { useAssetInfoRetrieval } from '@/composables/assets/retrieval';
import { usePriceUtils } from '@/modules/prices/use-price-utils';
import { TableId, useRememberTableSorting } from '@/modules/table/use-remember-table-sorting';
import { useGeneralSettingsStore } from '@/store/settings/general';
import { CURRENCY_USD } from '@/types/currencies';
import { getSortItems } from '@/utils/assets';
import { sum } from '@/utils/balances';
import { type AssetBalance, type BigNumber, Zero } from '@rotki/common';

interface AssetWithPrice extends AssetBalance {
  price: BigNumber;
}

interface AccountAssetBalancesProps {
  assets: AssetBalance[];
  title: string;
  flat?: boolean;
}

const props = withDefaults(defineProps<AccountAssetBalancesProps>(), {
  flat: false,
});

const { t } = useI18n({ useScope: 'global' });
const { assets } = toRefs(props);

const { assetPrice } = usePriceUtils();
const { currencySymbol } = storeToRefs(useGeneralSettingsStore());
const { assetInfo } = useAssetInfoRetrieval();
const getPrice = (asset: string) => get(assetPrice(asset)) ?? Zero;

const sort = ref<DataTableSortData<AssetWithPrice>>({
  column: 'usdValue',
  direction: 'desc' as const,
});

const assetsWithPrice = computed<AssetWithPrice[]>(() =>
  get(assets).map(row => ({ ...row, price: get(getPrice(row.asset)) })),
);

const sortItems = getSortItems<AssetWithPrice>(asset => get(assetInfo(asset)));

const sorted = computed<AssetWithPrice[]>(() => {
  const sortBy = get(sort);
  const data = [...get(assetsWithPrice)];
  if (!Array.isArray(sortBy) && sortBy?.column)
    return sortItems(data, [sortBy.column as keyof AssetBalance], [sortBy.direction === 'desc']);

  return data;
});

const totalValue = computed<BigNumber>(() => sum(get(assetsWithPrice)));

const headers = computed<DataTableColumn<AssetWithPrice>[]>(() => [
  {
    cellClass: 'py-1',
    class: 'text-no-wrap w-full',
    key: 'asset',
    label: t('common.asset'),
    sortable: true,
  },
  {
    align: 'end',
    cellClass: 'py-1',
    class: 'text-no-wrap',
    key: 'price',
    label: t('common.price_in_symbol', {
      symbol: get(currencySymbol),
    }),
    sortable: true,
  },
  {
    align: 'end',
    cellClass: 'py-1',
    class: 'text-no-wrap',
    key: 'amount',
    label: t('common.amount'),
    sortable: true,
  },
  {
    align: 'end',
    cellClass: 'py-1',
    class: 'text-no-wrap',
    key: 'usdValue',
    label: t('common.value_in_symbol', {
      symbol: get(currencySymbol),
    }),
    sortable: true,
  },
]);

useRememberTableSorting<AssetWithPrice>(TableId.ACCOUNT_ASSET_BALANCES, sort, headers);
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
          :asset="row.asset"
        />
      </template>
      <template #item.price="{ row }">
        <AmountDisplay
          v-if="assetPrice(row.asset).value"
          is-asset-price
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
      <template #item.usdValue="{ row }">
        <AmountDisplay
          fiat-currency="USD"
          :value="row.usdValue"
          show-currency="symbol"
        />
      </template>
      <template #body.append>
        <RowAppend
          label-colspan="3"
          :label="t('common.total')"
          class="[&>td]:p-4"
        >
          <AmountDisplay
            :fiat-currency="CURRENCY_USD"
            :value="totalValue"
            show-currency="symbol"
          />
        </RowAppend>
      </template>
    </RuiDataTable>
  </RuiCard>
</template>
