<script lang="ts" setup>
import type { Balance } from '@rotki/common';
import ChainBalanceTooltipIcon from '@/modules/balances/protocols/components/ChainBalanceTooltipIcon.vue';
import { sortDesc } from '@/modules/core/common/data/bignumbers';

const { chains } = defineProps<{
  chains: Record<string, Balance>;
  asset?: string;
  loading?: boolean;
}>();

/** Chains shown as logos; the rest collapse into a count, so a widely held asset keeps a short row. */
const MAX_SHOWN = 5;

const chainEntries = computed<[string, Balance][]>(() => Object.entries(chains).sort((a, b) => sortDesc(a[1].value, b[1].value)));

const shown = computed<[string, Balance][]>(() => get(chainEntries).slice(0, MAX_SHOWN));

const hiddenCount = computed<number>(() => Math.max(0, get(chainEntries).length - MAX_SHOWN));
</script>

<template>
  <!-- logos sit in equal round chips that overlap a little, so marks with different padding read as one group -->
  <div class="flex items-center -space-x-1.5">
    <div
      v-for="[chainId, chainBalance] in shown"
      :key="chainId"
      class="size-6 rounded-full bg-rui-surface border border-rui-divider flex items-center justify-center hover:z-1"
    >
      <ChainBalanceTooltipIcon
        :chain-id="chainId"
        :chain-balance="chainBalance"
        :asset="asset"
        :loading="loading"
      />
    </div>
    <div
      v-if="hiddenCount > 0"
      class="size-6 rounded-full bg-rui-surface-muted border border-rui-divider flex items-center justify-center text-[0.625rem] font-medium text-rui-text-secondary"
      data-testid="chain-balances-more"
    >
      +{{ hiddenCount }}
    </div>
  </div>
</template>
