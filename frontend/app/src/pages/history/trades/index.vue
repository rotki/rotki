<script setup lang="ts">
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
