<script setup lang="ts">
import { NoteLocation } from '@/types/notes';
import HistoryEventsView from '@/components/history/events/HistoryEventsView.vue';

definePage({
  meta: {
    canNavigateBack: true,
    noteLocation: NoteLocation.HISTORY_EVENTS,
  },
  name: 'history-events',
});
</script>

<template>
  <HistoryEventsView main-page />
</template>
