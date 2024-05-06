<script setup lang="ts">
import type { DefiAsset } from '@/types/defi/overview';

const props = defineProps<{
  asset: DefiAsset;
}>();

const { asset } = toRefs(props);

const evmIdentifier: ComputedRef<string> = computed(() =>
  createEvmIdentifierFromAddress(get(asset).tokenAddress),
);
</script>

<template>
  <div class="flex items-center">
    <AssetIcon
      size="32px"
      :identifier="evmIdentifier"
    />
    <span class="ml-3">{{ asset.tokenSymbol }}</span>
    <div class="grow" />
    <div class="flex flex-col items-end">
      <BalanceDisplay
        no-icon
        :asset="evmIdentifier"
        :value="asset.balance"
      />
    </div>
  </div>
</template>
