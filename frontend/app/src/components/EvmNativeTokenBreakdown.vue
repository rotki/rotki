<script setup lang="ts">
import { CURRENCY_USD } from '@/types/currencies';
import type { AssetBreakdown } from '@/types/blockchain/accounts';
import type { BigNumber } from '@rotki/common/lib';
import type { DataTableColumn, DataTableSortData } from '@rotki/ui-library';

const props = withDefaults(
  defineProps<{
    identifier: string;
    blockchainOnly?: boolean;
    showPercentage?: boolean;
    total?: BigNumber | null;
    breakdown?: AssetBreakdown[];
  }>(),
  {
    blockchainOnly: false,
    showPercentage: false,
    total: null,
  },
);

const { t } = useI18n();

const { identifier, blockchainOnly, showPercentage, total, breakdown: breakdownProps } = toRefs(props);
const { getBreakdown } = useBlockchainStore();
const { assetBreakdown } = useBalancesBreakdown();

const { getChain } = useSupportedChains();

const breakdowns = computed(() => {
  const asset = get(identifier);
  const breakdown = isDefined(breakdownProps)
    ? get(breakdownProps)
    : (
        get(blockchainOnly) ? get(getBreakdown(asset)) : get(assetBreakdown(asset))
      );

  return groupAssetBreakdown(breakdown, (item) => {
    // TODO: Remove this when https://github.com/rotki/rotki/issues/6725 is resolved.
    const location = item.location;
    return getChain(location, null) || location;
  });
});

const { currencySymbol } = storeToRefs(useGeneralSettingsStore());

const sort = ref<DataTableSortData<AssetBreakdown>>({
  column: 'usdValue',
  direction: 'desc' as const,
});

const tableHeaders = computed<DataTableColumn<AssetBreakdown>[]>(() => {
  const headers: DataTableColumn<AssetBreakdown>[] = [
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
    v-model:sort="sort"
    :cols="tableHeaders"
    :rows="breakdowns"
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
      <AmountDisplay :value="row.amount" />
    </template>
    <template #item.usdValue="{ row }">
      <AmountDisplay
        show-currency="symbol"
        :amount="row.amount"
        :price-asset="identifier"
        fiat-currency="USD"
        :value="row.usdValue"
      />
    </template>
    <template #item.percentage="{ row }">
      <PercentageDisplay
        :value="percentage(row.usdValue)"
        :asset-padding="0.1"
      />
    </template>
  </RuiDataTable>
</template>
