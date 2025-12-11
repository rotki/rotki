<script lang="ts" setup>
import type { Balance } from '@rotki/common';
import ChainBalanceTooltipIcon from '@/modules/balances/protocols/components/ChainBalanceTooltipIcon.vue';
import { sortDesc } from '@/utils/bignumbers';

const props = defineProps<{
  chains: Record<string, Balance>;
  asset?: string;
  loading?: boolean;
}>();

const chainEntries = computed<[string, Balance][]>(() => Object.entries(props.chains).sort((a, b) => sortDesc(a[1].value, b[1].value)));
</script>

<template>
  <div class="flex items-center gap-2">
    <ChainBalanceTooltipIcon
      v-for="([chainId, chainBalance], index) in chainEntries"
      :key="chainId"
      :chain-id="chainId"
      :chain-balance="chainBalance"
      :asset="asset"
      :loading="loading"
      :class="{ 'ml-[-4px]': index > 0 }"
    />
  </div>
</template>
