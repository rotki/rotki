import type { CalendarReminderTemporaryPayload } from '@/modules/calendar/reminder';
import { type DOMWrapper, mount, type VueWrapper } from '@vue/test-utils';
import { afterEach, assert, beforeEach, describe, expect, it, vi } from 'vitest';
import CalendarReminderEntry from '@/modules/calendar/CalendarReminderEntry.vue';
import '@test/i18n';

const HOUR = 60 * 60;
const DAY = HOUR * 24;

describe('calendarReminderEntry', () => {
  let wrapper: VueWrapper<InstanceType<typeof CalendarReminderEntry>>;

  const baseModel = (secsBefore: number = HOUR): CalendarReminderTemporaryPayload => ({
    identifier: 1,
    isTemporary: true,
    secsBefore,
  });

  beforeEach(() => {
    // AmountInput reads the thousand-separator settings from the store.
    setActivePinia(createPinia());
  });

  afterEach(() => {
    wrapper?.unmount();
  });

  function createWrapper(
    modelValue: CalendarReminderTemporaryPayload = baseModel(),
  ): VueWrapper<InstanceType<typeof CalendarReminderEntry>> {
    return mount(CalendarReminderEntry, { props: { latest: false, modelValue } });
  }

  function amountInput(): DOMWrapper<HTMLInputElement> {
    return wrapper.find<HTMLInputElement>('input');
  }

  function lastWriteBack(): CalendarReminderTemporaryPayload | undefined {
    const updates = wrapper.emitted<[CalendarReminderTemporaryPayload]>('update:modelValue');
    return updates?.at(-1)?.[0];
  }

  function unitOptions(): string[] {
    const options: unknown = wrapper.findComponent({ name: 'RuiMenuSelect' }).props('options');
    assert(Array.isArray(options));
    return options.map(option => String(Reflect.get(option, 'key')));
  }

  it('should split the seconds it is given into an amount and a unit', () => {
    wrapper = createWrapper(baseModel(2 * DAY));

    expect(amountInput().element.value).toBe('2');
  });

  // The largest unit that divides evenly wins, so 90 minutes stays in minutes rather than becoming
  // an hour and a half.
  it.each([
    [90 * 60, '90'],
    [2 * HOUR, '2'],
    [3 * DAY, '3'],
    [2 * 7 * DAY, '2'],
  ])('should pick the largest unit that divides %i seconds evenly', (seconds, expected) => {
    wrapper = createWrapper(baseModel(seconds));

    expect(amountInput().element.value).toBe(expected);
  });

  it('should offer the units from smallest to largest', () => {
    wrapper = createWrapper(baseModel(2 * DAY));

    expect(unitOptions()).toEqual(['minutes', 'hours', 'days', 'weeks']);
  });

  it('should write the edited value back in seconds', async () => {
    wrapper = createWrapper();

    await amountInput().setValue('3');
    await amountInput().trigger('blur');

    expect(lastWriteBack()?.secsBefore).toBe(3 * HOUR);
  });

  // 🔴 The write-back is gated on validity, and there is no other channel: an out-of-range row
  // leaves the model holding its previous value and says nothing to its parent.
  it('should not write back a value above the allowed ceiling', async () => {
    wrapper = createWrapper();

    await amountInput().setValue('99999');
    await amountInput().trigger('blur');

    expect(lastWriteBack()).toBeUndefined();
  });

  it('should not write back an empty amount', async () => {
    wrapper = createWrapper();

    await amountInput().setValue('');
    await amountInput().trigger('blur');

    expect(lastWriteBack()).toBeUndefined();
  });

  it('should not write back a zero amount', async () => {
    wrapper = createWrapper();

    await amountInput().setValue('0');
    await amountInput().trigger('blur');

    expect(lastWriteBack()).toBeUndefined();
  });

  // The write-back is silent, so the message is the only thing telling the user why nothing saved.
  it('should show the ceiling message once the amount is out of range', async () => {
    vi.useFakeTimers();
    wrapper = createWrapper();

    await amountInput().setValue('99999');
    // The message sits behind an enter transition, so it is not in the DOM immediately.
    await vi.advanceTimersByTimeAsync(700);

    expect(wrapper.find('.details').text()).toContain('calendar.reminder.validation.amount.max_value');
    vi.useRealTimers();
  });
});
