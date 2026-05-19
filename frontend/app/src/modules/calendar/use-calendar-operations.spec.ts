import type { CalendarEvent } from '@/modules/calendar/types';
import { flushPromises } from '@vue/test-utils';
import dayjs from 'dayjs';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { useCalendarOperations } from '@/modules/calendar/use-calendar-operations';

function makeEvent(overrides: Partial<CalendarEvent> = {}): CalendarEvent {
  return {
    autoDelete: false,
    color: '',
    description: '',
    identifier: 0,
    name: 'event',
    timestamp: 0,
    ...overrides,
  };
}

const deleteCalendarEvent = vi.fn();
const showErrorMessage = vi.fn();
const show = vi.fn();
const autoDeleteCalendarEntries = ref<boolean>(true);

vi.mock('@/modules/calendar/use-calendar-api', () => ({
  useCalendarApi: vi.fn().mockImplementation(() => ({ deleteCalendarEvent })),
}));

vi.mock('@/modules/core/common/use-confirm-store', () => ({
  useConfirmStore: vi.fn().mockImplementation(() => ({ show })),
}));

vi.mock('@/modules/core/notifications/use-notifications', () => ({
  getErrorMessage: vi.fn().mockImplementation((e: unknown) => (e instanceof Error ? e.message : String(e))),
  useNotifications: vi.fn().mockImplementation(() => ({ showErrorMessage })),
}));

vi.mock('@/modules/settings/use-general-settings-store', () => ({
  useGeneralSettingsStore: vi.fn().mockImplementation(() => ({ autoDeleteCalendarEntries })),
}));

describe('useCalendarOperations', () => {
  beforeEach(() => {
    deleteCalendarEvent.mockReset().mockResolvedValue(true);
    showErrorMessage.mockReset();
    show.mockReset();
    set(autoDeleteCalendarEntries, true);
  });

  describe('emptyEventForm', () => {
    it('should create a form anchored to the start of the supplied date', () => {
      const selected = ref(dayjs('2026-05-20T10:30:00Z'));
      const { emptyEventForm } = useCalendarOperations(selected, vi.fn());

      const seedDate = dayjs('2026-05-21T10:30:00Z');
      const form = emptyEventForm(seedDate);
      expect(form.identifier).toBe(0);
      expect(form.name).toBe('');
      expect(form.autoDelete).toBe(true);
      // start of the same calendar day in local time
      const expected = seedDate.set('hours', 0).set('minutes', 0).set('seconds', 0).unix();
      expect(form.timestamp).toBe(expected);
    });

    it('should fall back to selectedDate when no date is supplied', () => {
      const selected = ref(dayjs('2026-06-01T15:00:00Z'));
      const { emptyEventForm } = useCalendarOperations(selected, vi.fn());

      const form = emptyEventForm();
      const expected = dayjs('2026-06-01T15:00:00Z').set('hours', 0).set('minutes', 0).set('seconds', 0).unix();
      expect(form.timestamp).toBe(expected);
    });

    it('should reflect the current autoDeleteCalendarEntries setting', () => {
      set(autoDeleteCalendarEntries, false);
      const { emptyEventForm } = useCalendarOperations(ref(dayjs()), vi.fn());

      expect(emptyEventForm().autoDelete).toBe(false);
    });
  });

  describe('add', () => {
    it('should populate modelValue with an empty form and disable edit mode', () => {
      const { add, modelValue, editMode } = useCalendarOperations(ref(dayjs('2026-05-20')), vi.fn());

      add(dayjs('2026-05-22'));
      expect(get(modelValue)).toBeDefined();
      expect(get(modelValue)?.identifier).toBe(0);
      expect(get(editMode)).toBe(false);
    });
  });

  describe('edit', () => {
    it('should set modelValue without the date helper field and enable edit mode', () => {
      const { edit, modelValue, editMode } = useCalendarOperations(ref(dayjs()), vi.fn());

      edit({
        ...makeEvent({ identifier: 5, name: 'meeting', timestamp: 1_700_000_000, color: 'red' }),
        date: '2026-05-22',
      });

      expect(get(modelValue)).toBeDefined();
      expect(get(modelValue)?.identifier).toBe(5);
      expect(get(modelValue)).not.toHaveProperty('date');
      expect(get(editMode)).toBe(true);
    });
  });

  describe('deleteEvent', () => {
    it('should open a confirm dialog with the calendar delete copy', () => {
      const { deleteEvent } = useCalendarOperations(ref(dayjs()), vi.fn());
      deleteEvent();

      expect(show).toHaveBeenCalledOnce();
      const [config, callback] = show.mock.calls[0];
      expect(config).toHaveProperty('message');
      expect(config).toHaveProperty('title');
      expect(typeof callback).toBe('function');
    });

    it('should call the API, refresh, and clear modelValue when the confirm callback runs', async () => {
      const fetchData = vi.fn();
      const { edit, deleteEvent, modelValue } = useCalendarOperations(ref(dayjs()), fetchData);

      edit(makeEvent({ identifier: 7, name: 'x' }));
      deleteEvent();

      const callback = show.mock.calls[0][1];
      await callback();
      await flushPromises();

      expect(deleteCalendarEvent).toHaveBeenCalledWith(7);
      expect(fetchData).toHaveBeenCalledOnce();
      expect(get(modelValue)).toBeNull();
    });

    it('should surface an error notification when the API call fails', async () => {
      deleteCalendarEvent.mockRejectedValueOnce(new Error('server boom'));
      const { edit, deleteEvent } = useCalendarOperations(ref(dayjs()), vi.fn());

      edit(makeEvent({ identifier: 9, name: 'x' }));
      deleteEvent();
      const callback = show.mock.calls[0][1];
      await callback();
      await flushPromises();

      expect(showErrorMessage).toHaveBeenCalledOnce();
    });

    it('should do nothing when no event is currently selected', async () => {
      const { deleteEvent } = useCalendarOperations(ref(dayjs()), vi.fn());
      deleteEvent();
      const callback = show.mock.calls[0][1];
      await callback();
      await flushPromises();

      expect(deleteCalendarEvent).not.toHaveBeenCalled();
      expect(showErrorMessage).not.toHaveBeenCalled();
    });
  });
});
