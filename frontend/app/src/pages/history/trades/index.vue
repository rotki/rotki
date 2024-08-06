<script setup lang="ts">
import { NoteLocation } from '@/types/notes';

definePage({
  name: 'trades',
  meta: {
    noteLocation: NoteLocation.HISTORY_TRADES,
  },
});
</script>

<template>
  <ClosedTrades />
</template>
