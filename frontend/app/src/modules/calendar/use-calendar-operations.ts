import type { Dayjs } from 'dayjs';
import type { MaybeRefOrGetter, Ref } from 'vue';
import type { CalendarEvent } from '@/modules/calendar/types';
import { omit } from 'es-toolkit';
import { useSetting } from '@/modules/settings/use-setting';

interface UseCalendarOperationsReturn {
  add: (selectedDate?: Dayjs) => void;
  edit: (event: CalendarEvent & { date?: string }) => void;
  editMode: Readonly<Ref<boolean>>;
  emptyEventForm: (date?: Dayjs) => CalendarEvent;
  modelValue: Ref<CalendarEvent | undefined>;
}

export function useCalendarOperations(selectedDate: MaybeRefOrGetter<Dayjs>): UseCalendarOperationsReturn {
  const autoDeleteCalendarEntries = useSetting('autoDeleteCalendarEntries');

  const modelValue = ref<CalendarEvent>();
  const editMode = shallowRef<boolean>(false);

  function emptyEventForm(date?: Dayjs): CalendarEvent {
    const startOfTheDate = (date ?? toValue(selectedDate)).set('hours', 0).set('minutes', 0).set('seconds', 0);
    const timestamp = startOfTheDate.unix();

    return {
      address: undefined,
      autoDelete: get(autoDeleteCalendarEntries),
      blockchain: undefined,
      color: '',
      counterparty: undefined,
      description: '',
      identifier: 0,
      name: '',
      timestamp,
    };
  }

  function add(selectedDate?: Dayjs): void {
    set(modelValue, emptyEventForm(selectedDate));
    set(editMode, false);
  }

  function edit(event: CalendarEvent & { date?: string }): void {
    set(modelValue, omit(event, ['date']));
    set(editMode, true);
  }

  return {
    add,
    edit,
    editMode: readonly(editMode),
    emptyEventForm,
    modelValue,
  };
}
