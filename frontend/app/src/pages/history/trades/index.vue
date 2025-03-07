<script setup lang="ts">
import ClosedTrades from '@/components/history/trades/ClosedTrades.vue';
import { NoteLocation } from '@/types/notes';

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
