<script setup lang="ts">
import groupBy from 'lodash/groupBy';
import { type DataTableHeader } from 'vuetify';
import { CURRENCY_USD } from '@/types/currencies';

const props = withDefaults(
  defineProps<{
    identifier: string;
    blockchainOnly?: boolean;
  }>(),
  {
    blockchainOnly: false
  }
);

const { identifier, blockchainOnly } = toRefs(props);

const { getBreakdown: getBlockchainBreakdown } = useAccountBalances();
const { assetBreakdown } = useBalancesBreakdown();

const breakdowns = computed(() => {
  const asset = get(identifier);
  const data = get(blockchainOnly)
    ? get(getBlockchainBreakdown(asset))
    : get(assetBreakdown(asset));

  const grouped = groupBy(data, 'location');

  return Object.entries(grouped).map(([location, breakdown]) => {
    const balance = zeroBalance();
    return {
      location,
      balance: breakdown.reduce(
        (previousValue, currentValue) =>
          balanceSum(previousValue, currentValue.balance),
        balance
      )
    };
  });
});

const { t } = useI18n();
const { currencySymbol } = storeToRefs(useGeneralSettingsStore());

const tableHeaders = computed<DataTableHeader[]>(() => [
  {
    text: t('common.location').toString(),
    value: 'location',
    align: 'center',
    width: '120px'
  },
  {
    text: t('common.amount').toString(),
    value: 'balance.amount',
    align: 'end'
  },
  {
    text: t('asset_locations.header.value', {
      symbol: get(currencySymbol) ?? CURRENCY_USD
    }).toString(),
    value: 'balance.usdValue',
    align: 'end'
  }
]);
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
    </data-table>
  </v-sheet>
</template>
