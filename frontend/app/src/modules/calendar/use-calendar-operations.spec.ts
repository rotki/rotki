import type { CalendarEvent } from '@/modules/calendar/types';
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

const autoDeleteCalendarEntries = ref<boolean>(true);

vi.mock('@/modules/settings/use-setting', () => ({
  useSetting: vi.fn(() => autoDeleteCalendarEntries),
}));

describe('useCalendarOperations', () => {
  beforeEach(() => {
    set(autoDeleteCalendarEntries, true);
  });

  describe('emptyEventForm', () => {
    it('should create a form anchored to the start of the supplied date', () => {
      const selected = ref(dayjs('2026-05-20T10:30:00Z'));
      const { emptyEventForm } = useCalendarOperations(selected);

      const seedDate = dayjs('2026-05-21T10:30:00Z');
      const form = emptyEventForm(seedDate);
      expect(form.identifier).toBe(0);
      expect(form.name).toBe('');
      expect(form.autoDelete).toBe(true);
      const startOfTheSameLocalDay = seedDate.set('hours', 0).set('minutes', 0).set('seconds', 0).unix();
      expect(form.timestamp).toBe(startOfTheSameLocalDay);
    });

    it('should fall back to selectedDate when no date is supplied', () => {
      const selected = ref(dayjs('2026-06-01T15:00:00Z'));
      const { emptyEventForm } = useCalendarOperations(selected);

      const form = emptyEventForm();
      const expected = dayjs('2026-06-01T15:00:00Z').set('hours', 0).set('minutes', 0).set('seconds', 0).unix();
      expect(form.timestamp).toBe(expected);
    });

    it('should reflect the current autoDeleteCalendarEntries setting', () => {
      set(autoDeleteCalendarEntries, false);
      const { emptyEventForm } = useCalendarOperations(ref(dayjs()));

      expect(emptyEventForm().autoDelete).toBe(false);
    });
  });

  describe('add', () => {
    it('should populate modelValue with an empty form and disable edit mode', () => {
      const { add, modelValue, editMode } = useCalendarOperations(ref(dayjs('2026-05-20')));

      add(dayjs('2026-05-22'));
      expect(get(modelValue)).toBeDefined();
      expect(get(modelValue)?.identifier).toBe(0);
      expect(get(editMode)).toBe(false);
    });
  });

  describe('edit', () => {
    it('should set modelValue without the date helper field and enable edit mode', () => {
      const { edit, modelValue, editMode } = useCalendarOperations(ref(dayjs()));

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
});
