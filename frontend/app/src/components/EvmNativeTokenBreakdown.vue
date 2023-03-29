<script setup lang="ts">
import { groupBy } from 'lodash';
import { type DataTableHeader } from 'vuetify';
import { type BigNumber } from '@rotki/common/lib';
import { useAccountBalancesStore } from '@/store/blockchain/accountbalances';
import { useBalancesBreakdownStore } from '@/store/balances/breakdown';
import { zeroBalance } from '@/utils/bignumbers';
import { balanceSum, calculatePercentage } from '@/utils/calculation';
import { CURRENCY_USD } from '@/types/currencies';
import { useGeneralSettingsStore } from '@/store/settings/general';

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

const { getBreakdown: getBlockchainBreakdown } = useAccountBalancesStore();
const { assetBreakdown } = useBalancesBreakdownStore();

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

const { tc } = useI18n();
const { currencySymbol } = storeToRefs(useGeneralSettingsStore());

const tableHeaders = computed<DataTableHeader[]>(() => {
  const headers: DataTableHeader[] = [
    {
      text: tc('common.location'),
      value: 'location',
      align: 'center',
      class: 'text-no-wrap'
    },
    {
      text: tc('common.amount'),
      value: 'balance.amount',
      align: 'end',
      width: '60%'
    },
    {
      text: tc('asset_locations.header.value', 0, {
        symbol: get(currencySymbol) ?? CURRENCY_USD
      }),
      value: 'balance.usdValue',
      align: 'end'
    }
  ];

  if (get(showPercentage)) {
    headers.push({
      text: tc('asset_locations.header.percentage'),
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
