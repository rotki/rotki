<script setup lang="ts">
import { NoteLocation } from '@/types/notes';
import CalendarView from '@/components/calendar/CalendarView.vue';

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
