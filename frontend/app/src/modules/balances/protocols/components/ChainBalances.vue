<script lang="ts" setup>
import type { Balance } from '@rotki/common';
import ChainBalanceTooltipIcon from '@/modules/balances/protocols/components/ChainBalanceTooltipIcon.vue';

defineProps<{
  chains: Record<string, Balance>;
  asset?: string;
  loading?: boolean;
}>();
</script>

<template>
  <div class="flex items-center gap-2">
    <ChainBalanceTooltipIcon
      v-for="([chainId, chainBalance], index) in Object.entries(chains)"
      :key="chainId"
      :chain-id="chainId"
      :chain-balance="chainBalance"
      :asset="asset"
      :loading="loading"
      :class="{ 'ml-[-4px]': index > 0 }"
    />
  </div>
</template>
