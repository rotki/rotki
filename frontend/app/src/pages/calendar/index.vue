<script setup lang="ts">
import CalendarView from '@/modules/calendar/CalendarView.vue';
import { NoteLocation } from '@/modules/core/common/notes';

definePage({
  meta: {
    canNavigateBack: true,
    noteLocation: NoteLocation.CALENDAR,
  },
  props: true,
});
</script>

<template>
  <CalendarView />
</template>
