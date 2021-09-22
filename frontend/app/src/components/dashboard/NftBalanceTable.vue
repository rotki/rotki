<template>
  <card v-if="balances.length > 0" outlined-body>
    <template #title>{{ $t('nft_balance_table.title') }}</template>
    <data-table :headers="tableHeaders" :items="balances" sort-by="priceUsd">
      <template #item.priceUsd="{ item }">
        <amount-display
          :value="item.priceUsd"
          show-currency="symbol"
          fiat-currency="USD"
        />
      </template>
    </data-table>
  </card>
</template>

<script lang="ts">
import { computed, defineComponent } from '@vue/composition-api';
import { DataTableHeader } from 'vuetify';
import i18n from '@/i18n';
import { NftBalance } from '@/store/balances/types';
import { useStore } from '@/store/utils';

const tableHeaders: DataTableHeader[] = [
  {
    text: i18n.t('nft_balance_table.column.id').toString(),
    value: 'id',
    cellClass: 'text-no-wrap'
  },
  {
    text: i18n.t('nft_balance_table.column.name').toString(),
    value: 'name',
    cellClass: 'text-no-wrap'
  },
  {
    text: i18n.t('nft_balance_table.column.price').toString(),
    value: 'priceUsd',
    align: 'end',
    width: '75%'
  }
];

export default defineComponent({
  name: 'NftBalanceTable',
  setup() {
    const store = useStore();
    const balances = computed<NftBalance[]>(
      () => store.getters['balances/nftBalances']
    );
    return {
      balances,
      tableHeaders
    };
  }
});
</script>

<style module lang="scss"></style>
