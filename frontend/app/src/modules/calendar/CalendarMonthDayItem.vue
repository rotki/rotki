<script setup lang="ts">
import type { Dayjs } from 'dayjs';
import type { CalendarEvent } from '@/modules/calendar/types';

const { day, events, isPast, isToday, isSelected } = defineProps<{
  day: {
    date: Dayjs;
    isCurrentMonth: boolean;
  };
  isPast: boolean;
  isToday: boolean;
  isSelected: boolean;
  events: CalendarEvent[];
}>();

const emit = defineEmits<{
  'select-date': [];
  'edit': [event: CalendarEvent];
  'add': [];
}>();

const label = computed<string>(() => day.date.format('D'));

function selectDate() {
  emit('select-date');
}

function edit(event: CalendarEvent) {
  emit('edit', event);
}

function add() {
  emit('add');
}

const visibleEvents = computed<CalendarEvent[]>(() => {
  if (events.length <= 3)
    return events;

  return events.slice(0, 2);
});

const hidden = computed<number>(() => events.length - get(visibleEvents).length);

const { t } = useI18n({ useScope: 'global' });
</script>

<template>
  <div
    class="group relative flex h-28 cursor-pointer flex-col items-center p-1 transition-colors hover:bg-rui-grey-50 dark:hover:bg-white/5"
    :class="{
      '*:opacity-30': !day.isCurrentMonth,
    }"
    @click="selectDate()"
  >
    <div
      class="flex h-6 min-w-8 items-center justify-center rounded-full px-1.5 text-sm transition-colors"
      :class="{
        'bg-rui-primary font-medium text-white': isSelected,
        'bg-rui-primary-subtle font-medium text-rui-primary': isToday && !isSelected,
        'text-rui-text': !isToday && !isSelected,
      }"
    >
      {{ label }}
    </div>
    <div
      class="pt-1.5 w-full flex flex-col"
      @click.stop=""
    >
      <button
        v-for="event in visibleEvents"
        :key="event.identifier"
        type="button"
        class="flex w-full min-w-0 items-center gap-1.5 rounded-rui-control px-1.5 py-0.5 text-left text-xs transition-colors hover:bg-rui-grey-100 focus-visible:outline-2 focus-visible:outline-rui-primary dark:hover:bg-white/10"
        :class="isPast ? 'text-rui-text-disabled' : 'text-rui-text'"
        :title="event.name"
        data-testid="calendar-day-event"
        @click="edit(event)"
      >
        <span
          class="size-2 shrink-0 rounded-full"
          :class="{ 'bg-rui-grey-400': isPast }"
          :style="isPast ? undefined : { backgroundColor: `#${event.color}` }"
        />
        <span class="truncate">{{ event.name }}</span>
      </button>
    </div>
    <div
      v-if="hidden"
      class="w-full px-1 pt-1 text-xs font-medium text-rui-text-secondary"
    >
      {{ t('calendar.more_events', { hidden }) }}
    </div>
    <RuiButton
      size="sm"
      variant="outlined"
      color="secondary"
      class="p-1! absolute top-1 right-1 transition opacity-0 invisible group-hover:opacity-100 group-hover:visible"
      :aria-label="t('calendar.add_event')"
      @click="add()"
    >
      <RuiIcon
        size="14"
        name="lu-plus"
      />
    </RuiButton>
  </div>
</template>
