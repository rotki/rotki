<script setup lang="ts">
import { type PropType } from 'vue';
import { type Suggestion } from '@/types/filtering';
import { truncateAddress } from '@/filters';

const props = defineProps({
  suggestion: {
    required: true,
    type: Object as PropType<Suggestion>
  }
});

const { suggestion } = toRefs(props);

const { assetInfo } = useAssetInfoRetrieval();

const displayValue = computed(() => {
  const item = get(suggestion);

  const value = item.value;
  if (!item.asset) {
    return value;
  }

  let usedAsset = value;
  if (typeof usedAsset === 'string') {
    usedAsset = get(assetInfo(value));
  }

  if (!usedAsset) {
    return value;
  }

  if (usedAsset.evmChain) {
    return `${usedAsset.symbol} (${usedAsset.evmChain})`;
  }

  return usedAsset.isCustomAsset ? usedAsset.name : usedAsset.symbol;
});

const displayText = computed(() => {
  const truncated = truncateAddress(get(displayValue), 10);
  return `${get(suggestion).key}: ${truncated}`;
});
</script>

<template>
  <span class="font-weight-medium">
    {{ displayText }}
  </span>
</template>
