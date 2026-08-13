import type { CalendarEvent } from '@/modules/calendar/types';
import { mount, type VueWrapper } from '@vue/test-utils';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import '@test/i18n';

vi.mock('@/modules/calendar/use-calendar-reminder-api', () => ({
  useCalendarReminderApi: vi.fn().mockReturnValue({
    addCalendarReminder: vi.fn().mockResolvedValue({ failed: [] }),
    deleteCalendarReminder: vi.fn().mockResolvedValue(true),
    editCalendarReminder: vi.fn().mockResolvedValue(true),
    fetchCalendarReminders: vi.fn().mockResolvedValue([]),
  }),
}));

const CalendarForm = (await import('@/modules/calendar/CalendarForm.vue')).default;

describe('calendarForm', () => {
  let wrapper: VueWrapper<InstanceType<typeof CalendarForm>>;

  const baseModel = (): CalendarEvent => ({
    autoDelete: false,
    color: 'ffffff',
    counterparty: '',
    description: '',
    identifier: 1,
    name: 'an event',
    timestamp: 1700000000,
  });

  beforeEach(() => {
    setActivePinia(createPinia());
  });

  afterEach(() => {
    wrapper?.unmount();
  });

  function createWrapper(modelValue: CalendarEvent = baseModel()): VueWrapper<InstanceType<typeof CalendarForm>> {
    return mount(CalendarForm, {
      global: {
        stubs: {
          BlockchainAccountSelector: true,
          CalendarColorInput: true,
          CounterpartyInput: true,
          DateTimePicker: true,
        },
      },
      props: { editMode: false, errorMessages: {}, modelValue },
    });
  }

  /** Adds a reminder row, which starts at the 15 minute default. */
  async function addReminderRow(): Promise<void> {
    const buttons = wrapper.findAll('button');
    const add = buttons.find(button => button.text().includes('calendar.reminder.add_reminder'));
    expect(add).toBeDefined();
    await add!.trigger('click');
    await nextTick();
  }

  function reminderRows(): VueWrapper[] {
    return wrapper.findAllComponents({ name: 'CalendarReminderEntry' });
  }

  it('should pass validation when the name is filled', async () => {
    wrapper = createWrapper();

    expect(await wrapper.vm.validate()).toBe(true);
  });

  it('should fail validation when the name is empty', async () => {
    wrapper = createWrapper({ ...baseModel(), name: '' });

    expect(await wrapper.vm.validate()).toBe(false);
  });

  it('should render a reminder row once one is added', async () => {
    wrapper = createWrapper();
    await addReminderRow();

    expect(reminderRows()).toHaveLength(1);
  });

  it('should pass validation with a reminder row inside its allowed range', async () => {
    wrapper = createWrapper();
    await addReminderRow();

    expect(await wrapper.vm.validate()).toBe(true);
  });

  // The reminder rows run their own validation, and it reaches the parent's gate: a row above the
  // thirty-day ceiling has to stop the event from saving.
  it('should fail validation when a reminder row is out of range', async () => {
    wrapper = createWrapper();
    await addReminderRow();

    const row = reminderRows()[0];
    await row.find('input').setValue('99999');
    await nextTick();

    expect(await wrapper.vm.validate()).toBe(false);
  });
});
