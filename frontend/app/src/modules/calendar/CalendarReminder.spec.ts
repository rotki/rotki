import type { ComponentPublicInstance } from 'vue';
import type { CalendarEvent } from '@/modules/calendar/types';
import { mount, type VueWrapper } from '@vue/test-utils';
import flushPromises from 'flush-promises';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import '@test/i18n';

const HOUR = 60 * 60;

const mockDelete = vi.fn<(id: number) => Promise<boolean>>();
const mockFetch = vi.fn();

vi.mock('@/modules/calendar/use-calendar-reminder-api', () => ({
  useCalendarReminderApi: vi.fn().mockReturnValue({
    addCalendarReminder: vi.fn().mockResolvedValue({ failed: [] }),
    deleteCalendarReminder: async (id: number): Promise<boolean> => mockDelete(id),
    editCalendarReminder: vi.fn().mockResolvedValue(true),
    fetchCalendarReminders: (...args: unknown[]): unknown => mockFetch(...args),
  }),
}));

const CalendarReminder = (await import('@/modules/calendar/CalendarReminder.vue')).default;

describe('calendarReminder', () => {
  let wrapper: VueWrapper<InstanceType<typeof CalendarReminder>>;

  const event = (): CalendarEvent => ({
    autoDelete: false,
    color: 'ffffff',
    counterparty: '',
    description: '',
    identifier: 7,
    name: 'an event',
    timestamp: 1700000000,
  });

  /** Three saved reminders, deliberately distinct so a row can be told apart from its neighbours. */
  const saved = [
    { acknowledged: false, eventId: 7, identifier: 11, secsBefore: HOUR },
    { acknowledged: false, eventId: 7, identifier: 22, secsBefore: 2 * HOUR },
    { acknowledged: false, eventId: 7, identifier: 33, secsBefore: 3 * HOUR },
  ];

  beforeEach(() => {
    setActivePinia(createPinia());
    mockDelete.mockClear().mockResolvedValue(true);
    mockFetch.mockClear().mockResolvedValue(saved);
  });

  afterEach(() => {
    wrapper?.unmount();
  });

  async function createWrapper(): Promise<VueWrapper<InstanceType<typeof CalendarReminder>>> {
    const mounted = mount(CalendarReminder, { props: { editMode: true, modelValue: event() } });
    await flushPromises();
    return mounted;
  }

  function rows(): VueWrapper<ComponentPublicInstance<Record<string, unknown>>>[] {
    return wrapper.findAllComponents<ComponentPublicInstance<Record<string, unknown>>>({ name: 'CalendarReminderEntry' });
  }

  it('should render a row per saved reminder', async () => {
    wrapper = await createWrapper();

    expect(rows()).toHaveLength(3);
  });

  // Rows are addressed by position, so deleting the middle one is where an off-by-one would show.
  it('should delete the reminder the clicked row belongs to', async () => {
    wrapper = await createWrapper();

    await rows()[1].findAll('button').at(-1)!.trigger('click');
    await flushPromises();

    expect(mockDelete).toHaveBeenCalledWith(22);
    expect(mockDelete).toHaveBeenCalledTimes(1);
  });

  it('should leave the other rows in place after a delete', async () => {
    mockFetch.mockResolvedValueOnce(saved).mockResolvedValueOnce([saved[0], saved[2]]);
    wrapper = await createWrapper();

    await rows()[1].findAll('button').at(-1)!.trigger('click');
    await flushPromises();

    // The rows are one, two and three hours, so the amounts say which ones survived.
    const remaining = rows().map(row => row.props('amount'));
    expect(remaining).toEqual(['1', '3']);
  });
});
