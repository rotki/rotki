<template>
  <div>
    <template v-if="!loopring">
      <account-asset-balances :title="$t('common.assets')" :assets="assets" />
      <account-asset-balances
        v-if="liabilities.length > 0"
        :title="$t('account_balance_table.liabilities')"
        :assets="liabilities"
      />
    </template>
    <account-asset-balances
      v-if="loopringBalances.length > 0"
      :title="loopring ? '' : $t('account_balance_table.loopring')"
      :assets="loopringBalances"
    />
  </div>
</template>

<script lang="ts">
import { AssetBalance } from '@rotki/common';
import { defineComponent, PropType } from 'vue';

export default defineComponent({
  name: 'AccountBalanceDetails',
  props: {
    loopring: {
      required: false,
      type: Boolean,
      default: false
    },
    assets: {
      required: true,
      type: Array as PropType<AssetBalance[]>
    },
    liabilities: {
      required: true,
      type: Array as PropType<AssetBalance[]>
    },
    loopringBalances: {
      required: true,
      type: Array as PropType<AssetBalance[]>
    }
  }
});
</script>
