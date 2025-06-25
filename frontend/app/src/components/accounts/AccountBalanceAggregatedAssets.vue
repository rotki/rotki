<script lang="ts" setup>
import AssetBalances from '@/components/AssetBalances.vue';
import { useAggregatedBalances } from '@/composables/balances/use-aggregated-balances';

const props = defineProps<{
  groupId: string;
  chains: string[];
}>();

const { chains, groupId } = toRefs(props);

const { useBlockchainBalances } = useAggregatedBalances();
const balances = useBlockchainBalances(chains, groupId);
</script>

<template>
  <AssetBalances
    class="bg-white dark:bg-[#1E1E1E]"
    :balances="balances"
    :details="{
      groupId,
      chains,
    }"
  />
</template>
