<script setup lang="ts">
import AccountAssetBalances from '@/components/accounts/balances/AccountAssetBalances.vue';
import { useBlockchainStore } from '@/store/blockchain';

const props = defineProps<{
  chain: string;
  address: string;
}>();

const { t } = useI18n();
const { getAccountDetails } = useBlockchainStore();

const details = computed(() => getAccountDetails(props.chain, props.address));
</script>

<template>
  <div class="flex flex-col gap-4">
    <AccountAssetBalances
      :title="t('common.assets')"
      :assets="details.assets"
      :flat="details.liabilities.length === 0"
    />
    <AccountAssetBalances
      v-if="details.liabilities.length > 0"
      :title="t('account_balance_table.liabilities')"
      :assets="details.liabilities"
    />
  </div>
</template>
