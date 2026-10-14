<script setup lang="ts">
import type { CalendarEvent } from '@/modules/calendar/types';
import dayjs, { type Dayjs } from 'dayjs';

const selectedDate = defineModel<Dayjs>('selectedDate', { required: true });

const { event, visibleDate } = defineProps<{
  visibleDate: Dayjs;
  event: CalendarEvent;
}>();

const emit = defineEmits<{
  edit: [event: CalendarEvent];
}>();

const time = computed<string>(() => dayjs(event.timestamp * 1000).format('HH:mm'));

function onEventClicked(calendarEvent: CalendarEvent): void {
  if (!get(selectedDate).isSame(visibleDate, 'month'))
    set(selectedDate, dayjs(calendarEvent.timestamp * 1000));

  emit('edit', calendarEvent);
}
</script>

<template>
  <button
    type="button"
    class="-mx-2 flex w-[calc(100%+1rem)] items-start gap-3 rounded-rui-control p-2 text-left transition-colors hover:bg-rui-grey-100 focus-visible:outline-2 focus-visible:outline-rui-primary motion-reduce:transition-none dark:hover:bg-rui-grey-800"
    data-testid="calendar-event"
    :data-key="event.identifier"
    :data-event-name="event.name"
    @click="onEventClicked(event)"
  >
    <span
      class="mt-1.5 size-2.5 shrink-0 rounded-full"
      :style="{ backgroundColor: `#${event.color}` }"
    />
    <span class="flex min-w-0 flex-col">
      <span class="text-sm font-medium text-rui-text">
        {{ event.name }}
      </span>
      <span class="text-xs text-rui-text-secondary">
        {{ time }}
      </span>
      <span
        v-if="event.description"
        class="mt-0.5 line-clamp-2 text-sm text-rui-text-secondary"
        :title="event.description"
      >
        {{ event.description }}
      </span>
    </span>
  </button>
</template>
