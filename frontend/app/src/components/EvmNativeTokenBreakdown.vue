<script setup lang="ts">
import { type BigNumber } from '@rotki/common/lib';
import { type DataTableHeader } from '@/types/vuetify';
import { CURRENCY_USD } from '@/types/currencies';

const { t } = useI18n();

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
    total: null
  }
);

const { identifier, blockchainOnly, showPercentage, total } = toRefs(props);

const { getBreakdown: getBlockchainBreakdown } = useAccountBalances();
const { assetBreakdown } = useBalancesBreakdown();

const breakdowns = computed(() => {
  const asset = get(identifier);
  return get(blockchainOnly)
    ? get(getBlockchainBreakdown(asset))
    : get(assetBreakdown(asset));
});

const { currencySymbol } = storeToRefs(useGeneralSettingsStore());

const tableHeaders = computed<DataTableHeader[]>(() => {
  const headers: DataTableHeader[] = [
    {
      text: t('common.location'),
      value: 'location',
      align: 'center',
      width: '120px',
      class: 'text-no-wrap'
    },
    {
      text: t('common.amount'),
      value: 'balance.amount',
      align: 'end',
      width: '60%'
    },
    {
      text: t('asset_locations.header.value', {
        symbol: get(currencySymbol) ?? CURRENCY_USD
      }),
      value: 'balance.usdValue',
      align: 'end'
    }
  ];

  if (get(showPercentage)) {
    headers.push({
      text: t('asset_locations.header.percentage'),
      value: 'percentage',
      align: 'end',
      class: 'text-no-wrap',
      sortable: false
    });
  }

  return headers;
});

const percentage = (value: BigNumber) => {
  const totalVal = get(total);
  if (!totalVal) {
    return '';
  }
  return calculatePercentage(value, totalVal);
};
</script>

<template>
  <v-sheet outlined>
    <data-table
      :headers="tableHeaders"
      :items="breakdowns"
      sort-by="balance.amount"
    >
      <template #item.location="{ item }">
        <location-display
          :identifier="item.location"
          :detail-path="item.detailPath"
        />
      </template>
      <template #item.balance.amount="{ item }">
        <amount-display :value="item.balance.amount" />
      </template>
      <template #item.balance.usdValue="{ item }">
        <amount-display
          show-currency="symbol"
          :amount="item.balance.amount"
          :price-asset="identifier"
          fiat-currency="USD"
          :value="item.balance.usdValue"
        />
      </template>
      <template #item.percentage="{ item }">
        <percentage-display :value="percentage(item.balance.usdValue)" />
      </template>
    </data-table>
  </v-sheet>
</template>
