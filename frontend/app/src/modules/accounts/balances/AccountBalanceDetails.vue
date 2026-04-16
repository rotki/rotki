<script setup lang="ts">
import AccountAssetBalances from '@/modules/accounts/balances/AccountAssetBalances.vue';
import { useAggregatedBalances } from '@/modules/balances/use-aggregated-balances';

const selected = defineModel<string[] | undefined>('selected', { required: true });

const { chain, address, selectionMode } = defineProps<{
  chain: string;
  address: string;
  selectionMode?: boolean;
}>();

const { t } = useI18n({ useScope: 'global' });
const { useBlockchainBalances } = useAggregatedBalances();

const chains = computed<string[]>(() => [chain]);

const assets = useBlockchainBalances(chains, () => address);
const liabilities = useBlockchainBalances(chains, () => address, 'liabilities');
</script>

<template>
  <div class="flex flex-col gap-4">
    <AccountAssetBalances
      v-model:selected="selected"
      :title="t('common.assets')"
      :assets="assets"
      :flat="liabilities.length === 0"
      :selection-mode="selectionMode"
    />
    <AccountAssetBalances
      v-if="liabilities.length > 0"
      v-model:selected="selected"
      :title="t('account_balance_table.liabilities')"
      :assets="liabilities"
      :selection-mode="selectionMode"
    />
  </div>
</template>
