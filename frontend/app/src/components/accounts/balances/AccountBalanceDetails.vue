<script setup lang="ts">
import AccountAssetBalances from '@/components/accounts/balances/AccountAssetBalances.vue';
import { useAggregatedBalances } from '@/composables/balances/use-aggregated-balances';

const selected = defineModel<string[] | undefined>('selected', { required: true });

const props = defineProps<{
  chain: string;
  address: string;
  selectionMode?: boolean;
}>();

const { address, chain } = toRefs(props);
const { t } = useI18n({ useScope: 'global' });
const { useBlockchainBalances } = useAggregatedBalances();

const chains = computed<string[]>(() => [chain.value]);

const assets = useBlockchainBalances(chains, address);
const liabilities = useBlockchainBalances(chains, address, 'liabilities');
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
