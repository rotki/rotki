<script lang="ts" setup>
import type { CalendarEvent } from '@/modules/calendar/types';
import dayjs, { type Dayjs } from 'dayjs';
import CalendarMonthDayItem from '@/modules/calendar/CalendarMonthDayItem.vue';
import CalendarWeekdays from '@/modules/calendar/CalendarWeekdays.vue';

const selectedDate = defineModel<Dayjs>('selectedDate', { required: true });

const { eventsWithDate, today, visibleDate } = defineProps<{
  today: Dayjs;
  visibleDate: Dayjs;
  eventsWithDate: (CalendarEvent & { date: string })[];
}>();

const emit = defineEmits<{
  'update:range': [range: [number, number]];
  'edit': [event: CalendarEvent];
  'add': [selectedDate: Dayjs];
}>();

function setSelectedDate(day: Dayjs): void {
  set(selectedDate, day);
}

function edit(event: CalendarEvent): void {
  emit('edit', event);
}

function add(day: Dayjs): void {
  emit('add', day);
}

const month = computed<number>(() => Number(visibleDate.format('M')));
const year = computed<number>(() => Number(visibleDate.format('YYYY')));

function getWeekday(date: string | Dayjs) {
  const dayjsValue = typeof date === 'string' ? dayjs(date) : date;
  return dayjsValue.weekday();
}

const numberOfDaysInMonth = computed<number>(() => dayjs(visibleDate).daysInMonth());

const currentMonthDays = computed(() =>
  Array.from(new Array(get(numberOfDaysInMonth)), (_, index) => ({
    date: dayjs(`${get(year)}-${get(month)}-${index + 1}`),
    isCurrentMonth: true,
  })),
);

const previousMonthDays = computed(() => {
  const firstDayOfTheMonthWeekday = getWeekday(get(currentMonthDays)[0].date);
  const previousMonth = dayjs(`${get(year)}-${get(month)}-01`).subtract(1, 'month');

  const visibleNumberOfDaysFromPreviousMonth = firstDayOfTheMonthWeekday ? firstDayOfTheMonthWeekday - 1 : 6;

  const previousMonthLastMondayDayOfMonth = dayjs(get(currentMonthDays)[0].date)
    .subtract(visibleNumberOfDaysFromPreviousMonth, 'day')
    .date();

  return Array.from(new Array(visibleNumberOfDaysFromPreviousMonth), (_, index) => ({
    date: dayjs(`${previousMonth.year()}-${previousMonth.month() + 1}-${previousMonthLastMondayDayOfMonth + index}`),
    isCurrentMonth: false,
  }));
});

const nextMonthDays = computed(() => {
  const lastDayOfTheMonthWeekday = getWeekday(`${get(year)}-${get(month)}-${get(currentMonthDays).length}`);

  const nextMonth = dayjs(`${get(year)}-${get(month)}-01`).add(1, 'month');

  const visibleNumberOfDaysFromNextMonth = lastDayOfTheMonthWeekday
    ? 7 - lastDayOfTheMonthWeekday
    : lastDayOfTheMonthWeekday;

  return Array.from(new Array(visibleNumberOfDaysFromNextMonth), (_, index) => ({
    date: dayjs(`${nextMonth.year()}-${nextMonth.month() + 1}-${index + 1}`),
    isCurrentMonth: false,
  }));
});

const days = computed(() => [...get(previousMonthDays), ...get(currentMonthDays), ...get(nextMonthDays)]);

watchImmediate(days, (days) => {
  const firstDay = days[0].date;
  const lastDay = days.at(-1)!.date;

  const fromTimestamp = dayjs(firstDay).unix();
  const toTimestamp = dayjs(lastDay).unix();

  emit('update:range', [fromTimestamp, toTimestamp]);
});

const NO_EVENTS: CalendarEvent[] = [];

/**
 * The events grouped by day once per change of the event list. Each cell gets the same array back
 * until the events change, so selecting a day re-renders only the cells whose state flips, not all
 * 42 as when every render filtered the list again and handed each cell a new array.
 */
const eventsByDate = computed<Map<string, CalendarEvent[]>>(() => {
  const grouped = new Map<string, CalendarEvent[]>();
  for (const event of eventsWithDate) {
    const dayEvents = grouped.get(event.date);
    if (dayEvents)
      dayEvents.push(event);
    else
      grouped.set(event.date, [event]);
  }
  return grouped;
});

const cells = computed<{ key: string; day: { date: Dayjs; isCurrentMonth: boolean } }[]>(() =>
  get(days).map(day => ({ day, key: day.date.format('YYYY-MM-DD') })),
);

function getEvents(key: string): CalendarEvent[] {
  return get(eventsByDate).get(key) ?? NO_EVENTS;
}
</script>

<template>
  <div class="overflow-x-auto">
    <div
      class="grid grid-cols-7 [&>div:not(:nth-child(7n))]:border-r [&>div:not(:nth-child(7n))]:border-rui-divider min-w-160"
    >
      <CalendarWeekdays />
      <CalendarMonthDayItem
        v-for="({ day, key }, index) in cells"
        :key="key"
        :class="{ 'border-t': index > 6 }"
        :day="day"
        :events="getEvents(key)"
        :is-past="day.date.isBefore(today, 'day')"
        :is-selected="day.date.isSame(selectedDate, 'day')"
        :is-today="day.date.isSame(today, 'day')"
        class="border-rui-divider"
        @edit="edit($event)"
        @select-date="setSelectedDate(day.date)"
        @add="add(day.date)"
      />
    </div>
  </div>
</template>
