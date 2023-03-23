<script setup lang="ts">
import { type PropType } from 'vue';
import { type Suggestion } from '@/types/filtering';

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

const displayText = computed(
  () => `${get(suggestion).key}: ${get(displayValue)}`
);
</script>

<template>
  <span class="font-weight-medium">
    {{ displayText }}
  </span>
</template>
