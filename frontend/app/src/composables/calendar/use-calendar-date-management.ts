import type { ComputedRef, Ref } from 'vue';
import type { CalendarEvent } from '@/types/history/calendar';
import dayjs, { type Dayjs } from 'dayjs';

interface UseCalendarDateManagementReturn {
  selectedDate: Ref<Dayjs>;
  visibleDate: Ref<Dayjs>;
  selectedDateEvents: Ref<CalendarEvent[]>;
  setSelectedDate: (day: Dayjs) => void;
}

export function useCalendarDateManagement(
  eventsWithDate: ComputedRef<(CalendarEvent & { date: string })[]>,
  dateFormat: string,
): UseCalendarDateManagementReturn {
  const selectedDate = ref<Dayjs>(dayjs());
  const visibleDate = ref<Dayjs>(dayjs());
  const selectedDateEvents = ref<CalendarEvent[]>([]);

  function setSelectedDate(day: Dayjs): void {
    set(selectedDate, day);
  }

  // Watch selected date to update visible date
  watch(selectedDate, (selected) => {
    set(visibleDate, selected);
  });

  // Watch selected date and events to update selected date events
  watch([selectedDate, eventsWithDate], ([selectedDate, eventsWithDate]) => {
    const selectedDateFormatted = selectedDate.format(dateFormat);
    const events = eventsWithDate.filter(item => item.date === selectedDateFormatted);
    if (events.length === 0 && selectedDateFormatted !== get(visibleDate).format(dateFormat))
      return;

    set(selectedDateEvents, events);
  });

  return {
    selectedDate,
    selectedDateEvents,
    setSelectedDate,
    visibleDate,
  };
}
