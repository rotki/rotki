<script setup lang="ts">
import { NoteLocation } from '@/types/notes';

definePage({
  name: 'history-events',
  meta: {
    canNavigateBack: true,
    noteLocation: NoteLocation.HISTORY_EVENTS,
  },
});
</script>

<template>
  <HistoryEventsView main-page />
</template>
