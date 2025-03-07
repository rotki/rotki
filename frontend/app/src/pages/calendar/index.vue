<script setup lang="ts">
import CalendarView from '@/components/calendar/CalendarView.vue';
import { NoteLocation } from '@/types/notes';

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
