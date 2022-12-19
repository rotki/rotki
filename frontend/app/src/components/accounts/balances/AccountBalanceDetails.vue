<script setup lang="ts">
import { type PropType } from 'vue';
import { type Blockchain } from '@rotki/common/lib/blockchain';
import AccountAssetBalances from '@/components/accounts/balances/AccountAssetBalances.vue';

const props = defineProps({
  blockchain: {
    required: true,
    type: String as PropType<Blockchain>
  },
  address: {
    required: true,
    type: String
  },
  loopring: {
    required: false,
    type: Boolean,
    default: false
  }
});

const { tc } = useI18n();
const { blockchain, address } = toRefs(props);
const { liabilities, assets, loopringBalances } = useAccountDetails(
  blockchain,
  address
);
</script>

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
