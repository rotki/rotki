<script setup lang="ts">
import { type PropType } from 'vue';
import { type Blockchain } from '@rotki/common/lib/blockchain';

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

const { t } = useI18n();
const { blockchain, address } = toRefs(props);
const { liabilities, assets, loopringBalances } = useAccountDetails(
  blockchain,
  address
);
</script>

<template>
  <div>
    <template v-if="!loopring">
      <AccountAssetBalances :title="t('common.assets')" :assets="assets" />
      <AccountAssetBalances
        v-if="liabilities.length > 0"
        :title="t('account_balance_table.liabilities')"
        :assets="liabilities"
      />
    </template>
    <AccountAssetBalances
      v-if="loopringBalances.length > 0"
      :title="loopring ? '' : t('account_balance_table.loopring')"
      :assets="loopringBalances"
    />
  </div>
</template>
