<script setup lang="ts">
import { NoteLocation } from '@/types/notes';
import ClosedTrades from '@/components/history/trades/ClosedTrades.vue';

definePage({
  meta: {
    noteLocation: NoteLocation.HISTORY_TRADES,
  },
  name: 'trades',
});
</script>

<template>
  <ClosedTrades />
</template>
