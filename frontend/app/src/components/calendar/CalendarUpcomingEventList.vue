<script setup lang="ts">
import { computed } from 'vue';
import dayjs, { type Dayjs } from 'dayjs';
import type { CalendarEvent } from '@/types/history/calendar';

const selectedDate = defineModel<Dayjs>('selectedDate', { required: true });

const props = defineProps<{
  events: CalendarEvent[];
  visibleDate: Dayjs;
}>();

const emit = defineEmits<{
  (e: 'edit', event: CalendarEvent): void;
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
      v-for="(events, date) in groupedEvents"
      :key="date"
      class="flex flex-col gap-2"
    >
      <DateDisplay
        :timestamp="events[0].timestamp"
        no-time
        hide-tooltip
        class="cursor-pointer text-sm font-bold"
        @click="handleDateClick(events[0].timestamp)"
      />

      <div class="flex flex-col gap-4">
        <CalendarEventList
          v-for="event in events"
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
