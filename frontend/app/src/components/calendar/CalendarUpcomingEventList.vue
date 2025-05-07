<script setup lang="ts">
import type { CalendarEvent } from '@/types/history/calendar';
import CalendarEventList from '@/components/calendar/CalendarEventList.vue';
import DateDisplay from '@/components/display/DateDisplay.vue';
import dayjs, { type Dayjs } from 'dayjs';
import { computed } from 'vue';

const selectedDate = defineModel<Dayjs>('selectedDate', { required: true });

const props = defineProps<{
  events: CalendarEvent[];
  visibleDate: Dayjs;
}>();

const emit = defineEmits<{
  edit: [event: CalendarEvent];
}>();

const groupedEvents = computed(() => {
  const grouped: Record<string, CalendarEvent[]> = {};
  props.events.forEach((event) => {
    const date = dayjs(event.timestamp * 1000).format('YYYY-MM-DD');
    if (!grouped[date]) {
      grouped[date] = [];
    }
    grouped[date].push(event);
  });
  return grouped;
});

function handleDateClick(timestamp: number) {
  set(selectedDate, dayjs(timestamp * 1000));
}

function edit(event: CalendarEvent) {
  set(selectedDate, dayjs(event.timestamp * 1000));
  emit('edit', event);
}
</script>

<template>
  <div class="flex flex-col gap-4">
    <div
      v-for="(calendarEvents, date) in groupedEvents"
      :key="date"
      class="flex flex-col gap-2 items-start"
    >
      <DateDisplay
        :timestamp="calendarEvents[0].timestamp"
        no-time
        hide-tooltip
        class="rounded-sm cursor-pointer text-sm font-bold underline hover:bg-rui-grey-200 dark:hover:bg-rui-grey-800 px-1 transition-all"
        @click="handleDateClick(calendarEvents[0].timestamp)"
      />

      <div class="flex flex-col gap-4 w-full">
        <CalendarEventList
          v-for="event in calendarEvents"
          :key="event.identifier"
          v-model:selected-date="selectedDate"
          :visible-date="visibleDate"
          :event="event"
          @edit="edit(event)"
        />
      </div>
    </div>
  </div>
</template>
