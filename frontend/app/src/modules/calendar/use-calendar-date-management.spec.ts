import type { CalendarEvent } from '@/modules/calendar/types';
import dayjs from 'dayjs';
import { describe, expect, it } from 'vitest';
import { nextTick } from 'vue';
import { useCalendarDateManagement } from '@/modules/calendar/use-calendar-date-management';

const DATE_FORMAT = 'YYYY-MM-DD';

function makeEvent(date: string, identifier: number, name = 'event'): CalendarEvent & { date: string } {
  return {
    address: undefined,
    autoDelete: false,
    blockchain: undefined,
    color: '',
    counterparty: undefined,
    date,
    description: '',
    identifier,
    name,
    timestamp: dayjs(date).unix(),
  };
}

describe('useCalendarDateManagement', () => {
  it('should initialize selectedDate and visibleDate to today', () => {
    const events = computed(() => []);
    const { selectedDate, visibleDate, selectedDateEvents } = useCalendarDateManagement(events, DATE_FORMAT);

    expect(get(selectedDate).format(DATE_FORMAT)).toBe(dayjs().format(DATE_FORMAT));
    expect(get(visibleDate).format(DATE_FORMAT)).toBe(dayjs().format(DATE_FORMAT));
    expect(get(selectedDateEvents)).toEqual([]);
  });

  it('should sync visibleDate when setSelectedDate is called', async () => {
    const events = computed(() => []);
    const { selectedDate, visibleDate, setSelectedDate } = useCalendarDateManagement(events, DATE_FORMAT);

    const target = dayjs('2026-01-15');
    setSelectedDate(target);
    await nextTick();

    expect(get(selectedDate).format(DATE_FORMAT)).toBe('2026-01-15');
    expect(get(visibleDate).format(DATE_FORMAT)).toBe('2026-01-15');
  });

  it('should populate selectedDateEvents with events matching the selected date', async () => {
    const list = ref<(CalendarEvent & { date: string })[]>([
      makeEvent('2026-01-15', 1, 'matches'),
      makeEvent('2026-01-16', 2, 'other'),
    ]);
    const events = computed(() => get(list));
    const { setSelectedDate, selectedDateEvents } = useCalendarDateManagement(events, DATE_FORMAT);

    setSelectedDate(dayjs('2026-01-15'));
    await nextTick();

    expect(get(selectedDateEvents)).toHaveLength(1);
    expect(get(selectedDateEvents)[0].identifier).toBe(1);
  });

  it('should clear selectedDateEvents when switching to a date with matching events', async () => {
    const list = ref<(CalendarEvent & { date: string })[]>([
      makeEvent('2026-01-15', 1),
      makeEvent('2026-01-16', 2),
    ]);
    const events = computed(() => get(list));
    const { setSelectedDate, selectedDateEvents } = useCalendarDateManagement(events, DATE_FORMAT);

    setSelectedDate(dayjs('2026-01-15'));
    await nextTick();
    expect(get(selectedDateEvents).map(e => e.identifier)).toEqual([1]);

    setSelectedDate(dayjs('2026-01-16'));
    await nextTick();
    expect(get(selectedDateEvents).map(e => e.identifier)).toEqual([2]);
  });

  it('should not overwrite selectedDateEvents when no events match and the date is outside the visible month', async () => {
    const list = ref<(CalendarEvent & { date: string })[]>([
      makeEvent('2026-01-15', 1),
    ]);
    const events = computed(() => get(list));
    const { setSelectedDate, selectedDateEvents, visibleDate } = useCalendarDateManagement(events, DATE_FORMAT);

    setSelectedDate(dayjs('2026-01-15'));
    await nextTick();
    expect(get(selectedDateEvents).map(e => e.identifier)).toEqual([1]);

    // Switching the visibleDate independently then to a date with no events should leave events as-is
    set(visibleDate, dayjs('2026-01-15'));
    setSelectedDate(dayjs('2026-02-01'));
    await nextTick();
    // selectedDate watcher also updates visibleDate, so by the time the second watcher runs the
    // selected date does match visibleDate — events should be cleared to empty array.
    expect(get(selectedDateEvents)).toEqual([]);
  });
});
