<script setup lang="ts">
import HistoryEventsView from '@/components/history/events/HistoryEventsView.vue';
import { NoteLocation } from '@/types/notes';

definePage({
  meta: {
    canNavigateBack: true,
    noteLocation: NoteLocation.HISTORY,
  },
  name: 'history-events',
});
</script>

<template>
  <HistoryEventsView main-page />
</template>
