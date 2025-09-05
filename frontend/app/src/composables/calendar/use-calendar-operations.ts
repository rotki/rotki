import type { Dayjs } from 'dayjs';
import type { Ref } from 'vue';
import type { CalendarEvent } from '@/types/history/calendar';
import { omit } from 'es-toolkit';
import { useCalendarApi } from '@/composables/history/calendar';
import { useConfirmStore } from '@/store/confirm';
import { useMessageStore } from '@/store/message';
import { useGeneralSettingsStore } from '@/store/settings/general';

interface UseCalendarOperationsReturn {
  add: (selectedDate?: Dayjs) => void;
  deleteEvent: () => void;
  edit: (event: CalendarEvent & { date?: string }) => void;
  editMode: Ref<boolean>;
  emptyEventForm: (date?: Dayjs) => CalendarEvent;
  modelValue: Ref<CalendarEvent | undefined>;
}

export function useCalendarOperations(
  selectedDate: Ref<Dayjs>,
  fetchData: () => void,
): UseCalendarOperationsReturn {
  const { t } = useI18n({ useScope: 'global' });
  const { deleteCalendarEvent } = useCalendarApi();
  const { show } = useConfirmStore();
  const { setMessage } = useMessageStore();
  const { autoDeleteCalendarEntries } = storeToRefs(useGeneralSettingsStore());

  const modelValue = ref<CalendarEvent>();
  const editMode = ref<boolean>(false);

  function emptyEventForm(date?: Dayjs): CalendarEvent {
    const startOfTheDate = (date || get(selectedDate)).set('hours', 0).set('minutes', 0).set('seconds', 0);
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

  async function deleteClicked(): Promise<void> {
    const item = get(modelValue);
    if (item) {
      try {
        await deleteCalendarEvent(item.identifier);
        fetchData();
        set(modelValue, null);
      }
      catch (error: any) {
        setMessage({
          description: t('calendar.delete_error.message', { message: error.message }),
          success: false,
          title: t('calendar.delete_event'),
        });
      }
    }
  }

  function deleteEvent(): void {
    show({
      message: t('calendar.dialog.delete.message'),
      title: t('calendar.delete_event'),
    }, deleteClicked);
  }

  return {
    add,
    deleteEvent,
    edit,
    editMode,
    emptyEventForm,
    modelValue,
  };
}
