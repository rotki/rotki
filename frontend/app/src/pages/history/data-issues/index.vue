<script setup lang="ts">
import { msg } from '@/message-key';
import { NoteLocation } from '@/modules/core/common/notes';
import DataIssuesView from '@/modules/history/data-issues/DataIssuesView.vue';

definePage({
  meta: {
    nav: { labelKey: msg.$t('navigation_menu.history_sub.data_issues'), icon: 'lu-shield-alert', parent: '/history/', order: 20, drawer: 'history-data-issues' },
    canNavigateBack: true,
    noteLocation: NoteLocation.HISTORY,
  },
});
</script>

<template>
  <DataIssuesView main-page />
</template>
