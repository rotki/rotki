<script lang="ts" setup>
import AssetBalances from '@/components/AssetBalances.vue';
import { useAggregatedBalances } from '@/composables/balances/use-aggregated-balances';

const selected = defineModel<string[] | undefined>('selected', { required: true });

const props = defineProps<{
  groupId: string;
  chains: string[];
  selectionMode?: boolean;
}>();

const { chains, groupId } = toRefs(props);

const { useBlockchainBalances } = useAggregatedBalances();
const balances = useBlockchainBalances(chains, groupId);
</script>

<template>
  <AssetBalances
    v-model:selected="selected"
    class="bg-white dark:bg-[#1E1E1E]"
    :balances="balances"
    show-per-protocol
    :selection-mode="selectionMode"
    :details="{
      groupId,
      chains,
    }"
  />
</template>
