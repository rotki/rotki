<script setup lang="ts">
import { NoteLocation } from '@/modules/core/common/notes';
import DataIssuesView from '@/modules/history/data-issues/DataIssuesView.vue';

definePage({
  meta: {
    canNavigateBack: true,
    noteLocation: NoteLocation.HISTORY,
  },
  name: 'history-data-issues',
});
</script>

<template>
  <DataIssuesView main-page />
</template>
