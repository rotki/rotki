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
      <template #item.priceInAsset="{ item }">
        <amount-display
          v-if="item.priceAsset !== currency"
          :value="item.priceInAsset"
          :asset="item.priceAsset"
        />
        <span v-else>-</span>
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
      <template #body.append="{ isMobile }">
        <tr>
          <td :colspan="isMobile ? 1 : 2" class="font-weight-medium">
            {{ $t('nft_balance_table.row.total') }}
          </td>
          <td class="text-right">
            <amount-display
              :value="total"
              show-currency="symbol"
              fiat-currency="USD"
            />
          </td>
          <td v-if="!isMobile" />
        </tr>
      </template>
    </data-table>
  </card>
</template>

<script lang="ts">
import { BigNumber } from '@rotki/common/';
import { computed, defineComponent, Ref } from '@vue/composition-api';
import { DataTableHeader } from 'vuetify';
import { currency } from '@/composables/session';
import i18n from '@/i18n';
import { Routes } from '@/router/routes';
import { BalanceActions } from '@/store/balances/action-types';
import { NonFungibleBalance } from '@/store/balances/types';
import { useStore } from '@/store/utils';
import { Zero } from '@/utils/bignumbers';

const tableHeaders = (currency: Ref<string>) => {
  return computed<DataTableHeader[]>(() => [
    {
      text: i18n.t('nft_balance_table.column.name').toString(),
      value: 'name',
      cellClass: 'text-no-wrap'
    },
    {
      text: i18n.t('nft_balance_table.column.price_in_asset').toString(),
      value: 'priceInAsset',
      align: 'end',
      width: '75%',
      class: 'text-no-wrap'
    },
    {
      text: i18n
        .t('nft_balance_table.column.price', {
          currency: currency.value
        })
        .toString(),
      value: 'usdPrice',
      align: 'end',
      class: 'text-no-wrap'
    },
    {
      text: i18n.t('nft_balance_table.column.percentage').toString(),
      value: 'percentage',
      align: 'end',
      class: 'text-no-wrap'
    }
  ]);
};

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
    const refresh = async () => {
      return await store.dispatch(
        `balances/${BalanceActions.FETCH_NF_BALANCES}`,
        true
      );
    };

    const total = computed(() => {
      return balances.value.reduce(
        (sum, value) => sum.plus(value.usdPrice),
        Zero
      );
    });
    return {
      percentage,
      balances,
      tableHeaders: tableHeaders(currency),
      currency,
      refresh,
      total,
      nonFungibleRoute: Routes.NON_FUNGIBLE
    };
  }
});
</script>
