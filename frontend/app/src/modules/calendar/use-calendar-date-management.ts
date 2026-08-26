import type { ComputedRef, Ref } from 'vue';
import type { CalendarEvent } from '@/modules/calendar/types';
import dayjs, { type Dayjs } from 'dayjs';

interface UseCalendarDateManagementReturn {
  modelSelectedDate: Ref<Dayjs>;
  modelVisibleDate: Ref<Dayjs>;
  selectedDateEvents: Readonly<Ref<CalendarEvent[]>>;
  setSelectedDate: (day: Dayjs) => void;
}

export function useCalendarDateManagement(
  eventsWithDate: ComputedRef<(CalendarEvent & { date: string })[]>,
  dateFormat: string,
): UseCalendarDateManagementReturn {
  const modelSelectedDate = ref<Dayjs>(dayjs());
  const modelVisibleDate = ref<Dayjs>(dayjs());
  const selectedDateEvents = ref<CalendarEvent[]>([]);

  function setSelectedDate(day: Dayjs): void {
    set(modelSelectedDate, day);
  }

  watch(modelSelectedDate, (selected) => {
    set(modelVisibleDate, selected);
  });

  watch([modelSelectedDate, eventsWithDate], ([modelSelectedDate, eventsWithDate]) => {
    const selectedDateFormatted = modelSelectedDate.format(dateFormat);
    const events = eventsWithDate.filter(item => item.date === selectedDateFormatted);
    if (events.length === 0 && selectedDateFormatted !== get(modelVisibleDate).format(dateFormat))
      return;

    set(selectedDateEvents, events);
  });

  return {
    modelSelectedDate,
    selectedDateEvents: shallowReadonly(selectedDateEvents),
    setSelectedDate,
    modelVisibleDate,
  };
}
