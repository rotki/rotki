<script setup lang="ts">
import AccountAssetBalances from '@/components/accounts/balances/AccountAssetBalances.vue';
import { useBlockchainAccountData } from '@/modules/balances/blockchain/use-blockchain-account-data';

const props = defineProps<{
  chain: string;
  address: string;
}>();

const { address, chain } = toRefs(props);
const { t } = useI18n({ useScope: 'global' });
const { useAccountDetails } = useBlockchainAccountData();

const details = useAccountDetails(chain, address);
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
