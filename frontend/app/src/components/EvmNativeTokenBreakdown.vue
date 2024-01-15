<script setup lang="ts">
import { CURRENCY_USD } from '@/types/currencies';
import type { BigNumber } from '@rotki/common/lib';
import type {
  DataTableColumn,
  DataTableSortData,
} from '@rotki/ui-library-compat';
import type { Ref } from 'vue';

const props = withDefaults(
  defineProps<{
    identifier: string;
    blockchainOnly?: boolean;
    showPercentage?: boolean;
    total?: BigNumber | null;
  }>(),
  {
    blockchainOnly: false,
    showPercentage: false,
    total: null,
  },
);

const { t } = useI18n();

const { identifier, blockchainOnly, showPercentage, total } = toRefs(props);

const { getBreakdown: getBlockchainBreakdown } = useAccountBalances();
const { assetBreakdown } = useBalancesBreakdown();

const breakdowns = computed(() => {
  const asset = get(identifier);
  const breakdown = get(blockchainOnly)
    ? get(getBlockchainBreakdown(asset))
    : get(assetBreakdown(asset));

  return groupAssetBreakdown(breakdown, item => item.location);
});

const { currencySymbol } = storeToRefs(useGeneralSettingsStore());

const sort: Ref<DataTableSortData> = ref({
  column: 'usdValue',
  direction: 'desc' as const,
});

const tableHeaders = computed<DataTableColumn[]>(() => {
  const headers: DataTableColumn[] = [
    {
      label: t('common.location'),
      key: 'location',
      align: 'center',
      class: 'text-no-wrap',
      cellClass: 'py-2',
      sortable: true,
    },
    {
      label: t('common.amount'),
      key: 'amount',
      align: 'end',
      class: 'w-full',
      cellClass: 'py-2',
      sortable: true,
    },
    {
      label: t('asset_locations.header.value', {
        symbol: get(currencySymbol) ?? CURRENCY_USD,
      }),
      key: 'usdValue',
      align: 'end',
      cellClass: 'py-2',
      sortable: true,
    },
  ];

  if (get(showPercentage)) {
    headers.push({
      label: t('asset_locations.header.percentage'),
      key: 'percentage',
      align: 'end',
      class: 'text-no-wrap',
      cellClass: 'py-2',
    });
  }

  return headers;
});

function percentage(value: BigNumber) {
  const totalVal = get(total);
  if (!totalVal)
    return '';

  return calculatePercentage(value, totalVal);
}
</script>

<template>
  <RuiDataTable
    :cols="tableHeaders"
    :rows="breakdowns"
    :sort.sync="sort"
    :empty="{ description: t('data_table.no_data') }"
    row-attr="location"
    outlined
  >
    <template #item.location="{ row }">
      <LocationDisplay
        :identifier="row.location"
        :detail-path="row.detailPath"
      />
    </template>
    <template #item.amount="{ row }">
      <AmountDisplay :value="row.balance.amount" />
    </template>
    <template #item.usdValue="{ row }">
      <AmountDisplay
        show-currency="symbol"
        :amount="row.balance.amount"
        :price-asset="identifier"
        fiat-currency="USD"
        :value="row.balance.usdValue"
      />
    </template>
    <template #item.percentage="{ row }">
      <PercentageDisplay
        :value="percentage(row.balance.usdValue)"
        :asset-padding="0.1"
      />
    </template>
  </RuiDataTable>
</template>
