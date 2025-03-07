<script setup lang="ts">
import type { CalendarEvent } from '@/types/history/calendar';
import type { Dayjs } from 'dayjs';

const props = defineProps<{
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
  (e: 'select-date'): void;
  (e: 'edit', event: CalendarEvent): void;
  (e: 'add'): void;
}>();

const { day, events, isPast } = toRefs(props);

const label = computed(() => get(day).date.format('D'));

function selectDate() {
  emit('select-date');
}

function edit(event: CalendarEvent) {
  emit('edit', event);
}

function add() {
  emit('add');
}

const visibleEvents = computed(() => {
  const eventsVal = get(events);
  if (eventsVal.length <= 3)
    return eventsVal;

  return eventsVal.slice(0, 2);
});

const hidden = computed(() => get(events).length - get(visibleEvents).length);

const { t } = useI18n();

const { isDark } = useRotkiTheme();

function getColor(isDark: boolean, color: string | undefined, isBg: boolean = false) {
  if (!color)
    return undefined;

  if (isDark)
    return isBg ? `#${color}80` : '#ffffff';

  return `#${color}${isBg ? '1a' : ''}`;
}
</script>

<template>
  <div
    class="flex flex-col items-center h-[7.5rem] p-1 relative group"
    :class="{
      '[&>*]:opacity-30': !day.isCurrentMonth,
    }"
    @click="selectDate()"
  >
    <div
      class="text-body-2 w-10 h-5 flex items-center justify-center rounded-full cursor-pointer transition-all"
      :class="{
        'bg-rui-primary text-white': isSelected,
        'bg-rui-primary-lighter text-rui-light-text': isToday && !isSelected,
        'hover:bg-rui-grey-100 dark:hover:bg-rui-grey-800': !isToday && !isSelected,
      }"
    >
      {{ label }}
    </div>
    <div
      class="pt-2 w-full flex flex-col gap-0.5"
      @click.stop=""
    >
      <RuiChip
        v-for="event in visibleEvents"
        :key="event.identifier"
        class="text-sm w-full"
        clickable
        size="sm"
        :title="event.name"
        :class="{
          'bg-rui-grey-400 !text-rui-text-disabled': isPast,
        }"
        :bg-color="isPast ? undefined : getColor(isDark, event.color, true)"
        :text-color="isPast ? undefined : getColor(isDark, event.color)"
        @click="edit(event)"
      >
        {{ event.name }}
      </RuiChip>
    </div>
    <div
      v-if="hidden"
      class="py-1.5 w-full text-sm text-rui-secondary font-medium"
    >
      {{ t('calendar.more_events', { hidden }) }}
    </div>
    <RuiButton
      size="sm"
      variant="outlined"
      color="secondary"
      class="!p-1 absolute top-1 right-1 transition opacity-0 invisible group-hover:opacity-100 group-hover:visible"
      @click="add()"
    >
      <RuiIcon
        size="14"
        name="lu-plus"
      />
    </RuiButton>
  </div>
</template>
