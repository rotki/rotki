<script lang="ts" setup>
import AssetBalances from '@/components/AssetBalances.vue';
import { useAccountAssetsSummary } from '@/modules/balances/use-account-assets-summary';

const props = defineProps<{
  groupId: string;
  chains: string[];
}>();

const { chains, groupId } = toRefs(props);

const { useAccountAssets } = useAccountAssetsSummary();
const assets = useAccountAssets(chains, groupId);
</script>

<template>
  <AssetBalances
    class="bg-white dark:bg-[#1E1E1E]"
    :balances="assets"
    :details="{
      groupId,
      chains,
    }"
  />
</template>
