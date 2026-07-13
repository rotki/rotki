<script setup lang="ts">
import { msg } from '@/message-key';
import CalendarView from '@/modules/calendar/CalendarView.vue';
import { NoteLocation } from '@/modules/core/common/notes';

definePage({
  meta: {
    nav: { labelKey: msg.$t('navigation_menu.calendar'), icon: 'lu-calendar-days', section: 4, order: 10, drawer: 'calendar' },
    canNavigateBack: true,
    noteLocation: NoteLocation.CALENDAR,
  },
  props: true,
});
</script>

<template>
  <CalendarView />
</template>
