<script setup lang="ts">
import { NoteLocation } from '@/modules/core/common/notes';
import HistoryEventsView from '@/modules/history/events/HistoryEventsView.vue';

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
