<script lang="ts" setup>
import type { CalendarEvent } from '@/types/history/calendar';
import CalendarMonthDayItem from '@/components/calendar/CalendarMonthDayItem.vue';
import CalendarWeekdays from '@/components/calendar/CalendarWeekdays.vue';
import dayjs, { type Dayjs } from 'dayjs';

const props = defineProps<{
  today: Dayjs;
  selectedDate: Dayjs;
  visibleDate: Dayjs;
  eventsWithDate: (CalendarEvent & { date: string })[];
}>();

const emit = defineEmits<{
  (e: 'update:selected-date', selectedDate: Dayjs): void;
  (e: 'update:range', range: [number, number]): void;
  (e: 'edit', event: CalendarEvent): void;
  (e: 'add'): void;
}>();

function setSelectedDate(day: Dayjs) {
  emit('update:selected-date', day);
}

function edit(event: CalendarEvent) {
  emit('edit', event);
}

function add() {
  emit('add');
}

const { eventsWithDate, selectedDate, today, visibleDate } = toRefs(props);

const month = computed(() => Number(get(visibleDate).format('M')));
const year = computed(() => Number(get(visibleDate).format('YYYY')));

function getWeekday(date: string | Dayjs) {
  const dayjsValue = typeof date === 'string' ? dayjs(date) : date;
  return dayjsValue.weekday();
}

const numberOfDaysInMonth = computed<number>(() => dayjs(get(visibleDate)).daysInMonth());

const currentMonthDays = computed(() =>
  [...new Array(get(numberOfDaysInMonth))].map((_, index) => ({
    date: dayjs(`${get(year)}-${get(month)}-${index + 1}`),
    isCurrentMonth: true,
  })),
);

const previousMonthDays = computed(() => {
  const firstDayOfTheMonthWeekday = getWeekday(get(currentMonthDays)[0].date);
  const previousMonth = dayjs(`${get(year)}-${get(month)}-01`).subtract(1, 'month');

  // Cover first day of the month being sunday (firstDayOfTheMonthWeekday === 0)
  const visibleNumberOfDaysFromPreviousMonth = firstDayOfTheMonthWeekday ? firstDayOfTheMonthWeekday - 1 : 6;

  const previousMonthLastMondayDayOfMonth = dayjs(get(currentMonthDays)[0].date)
    .subtract(visibleNumberOfDaysFromPreviousMonth, 'day')
    .date();

  return [...new Array(visibleNumberOfDaysFromPreviousMonth)].map((_, index) => ({
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

  return [...new Array(visibleNumberOfDaysFromNextMonth)].map((_, index) => ({
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

function getEvents(day: Dayjs) {
  return get(eventsWithDate).filter(item => item.date === day.format('YYYY-MM-DD'));
}
</script>

<template>
  <div class="overflow-x-auto">
    <div
      class="rounded-xl border border-default overflow-hidden grid grid-cols-7 [&>div:not(:nth-child(7n))]:border-r min-w-[56rem]"
    >
      <CalendarWeekdays />
      <CalendarMonthDayItem
        v-for="(day, index) in days"
        :key="day.date.toString()"
        :class="{ 'border-t': index > 6 }"
        :day="day"
        :events="getEvents(day.date)"
        :is-past="day.date.isBefore(today, 'day')"
        :is-selected="day.date.isSame(selectedDate, 'day')"
        :is-today="day.date.isSame(today, 'day')"
        class="border-default"
        @edit="edit($event)"
        @select-date="setSelectedDate(day.date)"
        @add="add()"
      />
    </div>
  </div>
</template>
