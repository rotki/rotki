import type { CalendarEvent } from '@/modules/calendar/types';
import { type ModelFormHarness, mountModelForm } from '@test/utils/model-form-harness';
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

  /** Mounts the form the way the dialog does, with a parent holding the event in a real ref. */
  function mountWithOwner(modelValue: CalendarEvent = baseModel()): ModelFormHarness<CalendarEvent> {
    return mountModelForm<CalendarEvent>(CalendarForm, {
      errors: {},
      global: {
        stubs: {
          BlockchainAccountSelector: true,
          CalendarColorInput: true,
          CounterpartyInput: true,
          DateTimePicker: true,
        },
      },
      payload: { ...modelValue },
      props: { editMode: false },
    });
  }

  it('should open without arming the unsaved-changes prompt', async () => {
    const harness = mountWithOwner();
    await nextTick();
    await nextTick();

    expect(harness.stateUpdated()).toBe(false);
    harness.wrapper.unmount();
  });

  it('should keep a typed name when the owner echoes the model back', async () => {
    const harness = mountWithOwner({ ...baseModel(), name: '' });

    await harness.wrapper.find('[data-testid=calendar-form-name] input').setValue('team standup');
    await nextTick();
    await nextTick();

    expect(await harness.validate()).toBe(true);
    harness.wrapper.unmount();
  });

  it('should hand the owner the name that was typed', async () => {
    const harness = mountWithOwner({ ...baseModel(), name: '' });

    await harness.wrapper.find('[data-testid=calendar-form-name] input').setValue('team standup');
    await nextTick();
    await nextTick();

    expect(harness.model().name).toBe('team standup');
    harness.wrapper.unmount();
  });

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

  it.each([
    ['autoDelete'],
    ['color'],
    ['counterparty'],
    ['description'],
    ['address'],
    ['blockchain'],
    ['identifier'],
  ] as const)('should still validate when %s is absent, being carried rather than validated', async (key) => {
    const model = baseModel();
    Reflect.deleteProperty(model, key);
    wrapper = createWrapper(model);

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

  it('should fail validation when a reminder row is out of range, its gate reaching the parent', async () => {
    wrapper = createWrapper();
    await addReminderRow();

    const row = reminderRows()[0];
    await row.find('input').setValue('99999');
    await nextTick();

    expect(await wrapper.vm.validate()).toBe(false);
  });
});
