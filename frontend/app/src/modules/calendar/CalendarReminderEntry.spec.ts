import { type DOMWrapper, mount, type VueWrapper } from '@vue/test-utils';
import { afterEach, assert, beforeEach, describe, expect, it } from 'vitest';
import CalendarReminderEntry from '@/modules/calendar/CalendarReminderEntry.vue';
import { ReminderUnit } from '@/modules/calendar/reminder-forms';
import '@test/i18n';

describe('calendarReminderEntry', () => {
  let wrapper: VueWrapper<InstanceType<typeof CalendarReminderEntry>>;

  beforeEach(() => {
    // AmountInput reads the thousand-separator settings from the store.
    setActivePinia(createPinia());
  });

  afterEach(() => {
    wrapper?.unmount();
  });

  function createWrapper(
    props: Record<string, unknown> = {},
  ): VueWrapper<InstanceType<typeof CalendarReminderEntry>> {
    return mount(CalendarReminderEntry, {
      props: { amount: '2', latest: false, unit: ReminderUnit.HOURS, ...props },
    });
  }

  function amountInput(): DOMWrapper<HTMLInputElement> {
    return wrapper.find<HTMLInputElement>('input');
  }

  function unitOptions(): string[] {
    const options: unknown = wrapper.findComponent({ name: 'RuiMenuSelect' }).props('options');
    assert(Array.isArray(options));
    return options.map(option => String(Reflect.get(option, 'key')));
  }

  it('should show the amount it is given', () => {
    wrapper = createWrapper({ amount: '90', unit: ReminderUnit.MINUTES });

    expect(amountInput().element.value).toBe('90');
  });

  it('should offer the units from smallest to largest', () => {
    wrapper = createWrapper();

    expect(unitOptions()).toEqual(['minutes', 'hours', 'days', 'weeks']);
  });

  // The row no longer decides whether a value is worth reporting: it reports what was typed, and
  // the list it belongs to validates. An out-of-range entry used to be swallowed here.
  it.each([
    ['99999'],
    [''],
    ['0'],
  ])('should report %s as typed rather than swallowing it', async (typed) => {
    wrapper = createWrapper();

    await amountInput().setValue(typed);

    expect(wrapper.emitted<[string]>('update:amount')?.at(-1)?.[0]).toBe(typed);
  });

  it('should show the messages it is handed', () => {
    wrapper = createWrapper({ errorMessages: ['too big'] });

    expect(wrapper.text()).toContain('too big');
  });

  it('should ask to be committed once the amount field is left', async () => {
    wrapper = createWrapper();

    await amountInput().setValue('3');
    await amountInput().trigger('blur');

    expect(wrapper.emitted('commit')).toHaveLength(1);
  });

  it('should ask to be committed as soon as the unit changes', async () => {
    wrapper = createWrapper();

    wrapper.findComponent({ name: 'RuiMenuSelect' }).vm.$emit('update:modelValue', ReminderUnit.DAYS);
    await nextTick();

    expect(wrapper.emitted<[string]>('update:unit')?.at(-1)?.[0]).toBe(ReminderUnit.DAYS);
    expect(wrapper.emitted('commit')).toHaveLength(1);
  });
});
