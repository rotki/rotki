<template>
  <card v-if="balances.length > 0" outlined-body>
    <template #title>
      {{ $t('nft_balance_table.title') }}
      <v-btn :to="nonFungibleRoute" icon class="ml-2">
        <v-icon>mdi-chevron-right</v-icon>
      </v-btn>
    </template>
    <data-table :headers="tableHeaders" :items="balances" sort-by="usdPrice">
      <template #item.name="{ item }">
        {{ item.name ? item.name : item.id }}
      </template>
      <template #item.usdPrice="{ item }">
        <amount-display
          :value="item.usdPrice"
          show-currency="symbol"
          fiat-currency="USD"
        />
      </template>
      <template #item.percentage="{ item }">
        <percentage-display :value="percentage(item.usdPrice)" />
      </template>
    </data-table>
  </card>
</template>

<script lang="ts">
import { computed, defineComponent } from '@vue/composition-api';
import { default as BigNumber } from 'bignumber.js';
import { DataTableHeader } from 'vuetify';
import i18n from '@/i18n';
import { Routes } from '@/router/routes';
import { NonFungibleBalance } from '@/store/balances/types';
import { useStore } from '@/store/utils';

const tableHeaders: DataTableHeader[] = [
  {
    text: i18n.t('nft_balance_table.column.name').toString(),
    value: 'name',
    cellClass: 'text-no-wrap'
  },
  {
    text: i18n.t('nft_balance_table.column.price').toString(),
    value: 'usdPrice',
    align: 'end',
    width: '75%'
  },
  {
    text: i18n.t('nft_balance_table.column.percentage').toString(),
    value: 'percentage',
    align: 'end',
    class: 'text-no-wrap'
  }
];

export default defineComponent({
  name: 'NftBalanceTable',
  setup() {
    const store = useStore();
    const balances = computed<NonFungibleBalance[]>(
      () => store.getters['balances/nfBalances']
    );

    const totalNetWorthUsd = computed<BigNumber>(
      () => store.getters['statistics/totalNetWorthUsd']
    );

    const percentage = (value: BigNumber) => {
      return value.div(totalNetWorthUsd.value).multipliedBy(100).toFixed(2);
    };
    return {
      percentage,
      balances,
      tableHeaders,
      nonFungibleRoute: Routes.NON_FUNGIBLE
    };
  }
});
</script>
