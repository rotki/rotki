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

const displayValue = computed(() => {
  const item = get(suggestion);

  const value = item.value;
  if (typeof value === 'string') {
    return value;
  }

  if (value.evmChain) {
    return `${value.symbol} (${value.evmChain})`;
  }

  return value.isCustomAsset ? value.name : value.symbol;
});

const displayText = computed(() => {
  return `${get(suggestion).key}: ${get(displayValue)}`;
});
</script>

<template>
  <span class="font-weight-medium">
    {{ displayText }}
  </span>
</template>
