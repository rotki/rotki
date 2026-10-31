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

  /**
   * Shows the selected day's events.
   *
   * @remarks
   * Only the visible month's events are loaded, so while another month is browsed the selected day
   * keeps the list it had. Inside the visible month an empty list is the truth: comparing with the
   * visible day instead missed month navigation, which moves the visible day on the 31st.
   */
  function showSelectedDateEvents([selected, eventsWithDate]: [Dayjs, (CalendarEvent & { date: string })[]]): void {
    const selectedDateFormatted = selected.format(dateFormat);
    const events = eventsWithDate.filter(item => item.date === selectedDateFormatted);
    if (events.length === 0 && !selected.isSame(get(modelVisibleDate), 'month'))
      return;

    set(selectedDateEvents, events);
  }

  watch([modelSelectedDate, eventsWithDate], showSelectedDateEvents);

  return {
    modelSelectedDate,
    selectedDateEvents: shallowReadonly(selectedDateEvents),
    setSelectedDate,
    modelVisibleDate,
  };
}
