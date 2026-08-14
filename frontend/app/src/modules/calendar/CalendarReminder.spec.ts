import type { ComponentPublicInstance } from 'vue';
import type { CalendarEvent } from '@/modules/calendar/types';
import { mount, type VueWrapper } from '@vue/test-utils';
import flushPromises from 'flush-promises';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import '@test/i18n';

const HOUR = 60 * 60;

const mockDelete = vi.fn<(id: number) => Promise<boolean>>();
const mockFetch = vi.fn();
const mockAdd = vi.fn();
const mockEdit = vi.fn();

vi.mock('@/modules/calendar/use-calendar-reminder-api', () => ({
  useCalendarReminderApi: vi.fn().mockReturnValue({
    addCalendarReminder: (...args: unknown[]): unknown => mockAdd(...args),
    deleteCalendarReminder: async (id: number): Promise<boolean> => mockDelete(id),
    editCalendarReminder: (...args: unknown[]): unknown => mockEdit(...args),
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
    mockAdd.mockClear().mockResolvedValue({ failed: [] });
    mockEdit.mockClear().mockResolvedValue(true);
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

  async function deleteMiddleRow(): Promise<void> {
    await rows()[1].findAll('button').at(-1)!.trigger('click');
    await flushPromises();
  }

  it('should render a row per saved reminder', async () => {
    wrapper = await createWrapper();

    expect(rows()).toHaveLength(3);
  });

  // Rows are removed by position, so dropping the middle one is where an off-by-one would show. The
  // rows are one, two and three hours, so the amounts say which ones survived.
  it('should drop only the clicked row', async () => {
    wrapper = await createWrapper();

    await deleteMiddleRow();

    expect(rows().map(row => row.props('amount'))).toEqual(['1', '3']);
  });

  // The rows are the dialog's to save. Writing one the moment it is edited meant a cancelled dialog
  // still changed the event, which is the whole reason persistence moved to `save`.
  it('should not touch the server when a row is deleted', async () => {
    wrapper = await createWrapper();

    await deleteMiddleRow();

    expect(mockDelete).not.toHaveBeenCalled();
  });

  it('should delete the reminder the dropped row belonged to once saved', async () => {
    wrapper = await createWrapper();

    await deleteMiddleRow();
    await wrapper.vm.save(7);

    expect(mockDelete).toHaveBeenCalledWith(22);
    expect(mockDelete).toHaveBeenCalledTimes(1);
  });

  it('should create a reminder for a row added since the event was loaded', async () => {
    wrapper = await createWrapper();

    await wrapper.find('[data-testid=reminder-add]').trigger('click');
    await flushPromises();
    await wrapper.vm.save(7);

    // The button seeds a row at the fifteen minute default.
    expect(mockAdd).toHaveBeenCalledWith([{ eventId: 7, secsBefore: 900 }]);
  });

  it('should not write anything when nothing was edited', async () => {
    wrapper = await createWrapper();

    await wrapper.vm.save(7);

    expect(mockDelete).not.toHaveBeenCalled();
    expect(mockAdd).not.toHaveBeenCalled();
    expect(mockEdit).not.toHaveBeenCalled();
  });
});
