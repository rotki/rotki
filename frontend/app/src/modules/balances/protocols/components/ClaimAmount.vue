<script setup lang="ts">
import type { BigNumber } from '@rotki/common';
import { AssetAmountDisplay, ValueDisplay } from '@/modules/assets/amount-display/components';

defineProps<{
  amount: BigNumber;
  /** Shown with the asset's symbol when known, as a bare amount otherwise. */
  asset?: string;
}>();
</script>

<template>
  <AssetAmountDisplay
    v-if="asset"
    :asset="asset"
    :amount="amount"
  />
  <ValueDisplay
    v-else
    :value="amount"
  />
</template>
