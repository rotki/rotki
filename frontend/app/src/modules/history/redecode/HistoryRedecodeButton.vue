<script setup lang="ts">
import type { DecodeScope } from '@/modules/history/events/event-payloads';
import { checkIfDevelopment } from '@shared/utils';
import HistoryRedecodeSelection from '@/modules/history/redecode/HistoryRedecodeSelection.vue';

/** One button opening the chain picker; picking every chain is the full redecode, which confirms first. */
defineProps<{
  processing: boolean;
}>();

const emit = defineEmits<{ redecode: [scope: DecodeScope] }>();

const isDemoMode = import.meta.env.VITE_DEMO_MODE !== undefined;
const isDevelopment = checkIfDevelopment();
</script>

<template>
  <HistoryRedecodeSelection
    :loading="processing"
    :disabled="processing"
    :show-redecode-page="isDevelopment && !isDemoMode"
    @redecode="emit('redecode', $event)"
  />
</template>
