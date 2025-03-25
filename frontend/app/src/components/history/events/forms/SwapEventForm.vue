<script setup lang="ts">
import type { EventData, SwapEvent } from '@/types/history/events';

withDefaults(defineProps<{
  data?: EventData<SwapEvent>;
}>(), {
  data: undefined,
});
</script>

<template>
  <div />
</template>
