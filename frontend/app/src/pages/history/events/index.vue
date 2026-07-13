<script setup lang="ts">
import { msg } from '@/message-key';
import { NoteLocation } from '@/modules/core/common/notes';
import HistoryEventsView from '@/modules/history/events/HistoryEventsView.vue';

definePage({
  meta: {
    nav: { labelKey: msg.$t('navigation_menu.history_sub.events'), icon: 'lu-list', parent: '/history/', order: 10, drawer: 'history-events' },
    canNavigateBack: true,
    noteLocation: NoteLocation.HISTORY,
  },
});
</script>

<template>
  <HistoryEventsView main-page />
</template>
