<template>
  <div>
    <template v-if="!loopring">
      <account-asset-balances :title="tc('common.assets')" :assets="assets" />
      <account-asset-balances
        v-if="liabilities.length > 0"
        :title="tc('account_balance_table.liabilities')"
        :assets="liabilities"
      />
    </template>
    <account-asset-balances
      v-if="loopringBalances.length > 0"
      :title="loopring ? '' : tc('account_balance_table.loopring')"
      :assets="loopringBalances"
    />
  </div>
</template>

<script setup lang="ts">
import { AssetBalance } from '@rotki/common';
import { PropType } from 'vue';
import AccountAssetBalances from '@/components/accounts/balances/AccountAssetBalances.vue';

defineProps({
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
});

const { tc } = useI18n();
</script>
