<script lang="ts" setup>
import AssetBalances from '@/modules/balances/AssetBalances.vue';
import { useAggregatedBalances } from '@/modules/balances/use-aggregated-balances';

const selected = defineModel<string[] | undefined>('selected', { required: true });

const { groupId, chains, selectionMode } = defineProps<{
  groupId: string;
  chains: string[];
  selectionMode?: boolean;
}>();

const { useBlockchainBalances } = useAggregatedBalances();

const balances = useBlockchainBalances(() => chains, () => groupId);
</script>

<template>
  <AssetBalances
    v-model:selected="selected"
    class="bg-white dark:bg-dark-elevated"
    :balances="balances"
    show-per-protocol
    :selection-mode="selectionMode"
    :details="{
      groupId,
      chains,
    }"
  />
</template>
