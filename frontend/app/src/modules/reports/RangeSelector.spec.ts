import type { ComponentPublicInstance, Ref } from 'vue';
import { mount, type VueWrapper } from '@vue/test-utils';
import dayjs from 'dayjs';
import { afterEach, assert, beforeEach, describe, expect, it, vi } from 'vitest';
import { Quarter } from '@/modules/settings/types/frontend-settings';
import '@test/i18n';

interface ReportPeriod {
  quarter: Quarter;
  year: string;
}

const period = ref<ReportPeriod>({ quarter: Quarter.Q1, year: '2024' });
const updateFrontendSetting = vi.fn();

vi.mock('@/modules/settings/use-setting', () => ({
  useSetting: vi.fn().mockImplementation((): Ref<ReportPeriod> => period),
}));

vi.mock('@/modules/settings/use-settings-operations', () => ({
  useSettingsOperations: vi.fn().mockImplementation(() => ({ updateFrontendSetting })),
}));

const RangeSelector = (await import('@/modules/reports/RangeSelector.vue')).default;

/** The stubs below declare their props at runtime, so their instances are typed loosely. */
type StubInstance = ComponentPublicInstance<Record<string, unknown>>;

interface Range {
  end: number;
  start: number | undefined;
}

describe('rangeSelector', () => {
  let wrapper: VueWrapper<InstanceType<typeof RangeSelector>>;

  beforeEach(() => {
    vi.clearAllMocks();
    set(period, { quarter: Quarter.Q1, year: '2024' });
    vi.useFakeTimers();
    vi.setSystemTime(new Date('2026-08-14T00:00:00Z'));
  });

  afterEach(() => {
    wrapper?.unmount();
    vi.useRealTimers();
  });

  function createWrapper(modelValue: Range = { end: 1700000000, start: 1600000000 }): VueWrapper<InstanceType<typeof RangeSelector>> {
    return mount(RangeSelector, {
      global: {
        stubs: {
          DateTimeRangePicker: {
            emits: ['update:start', 'update:end'],
            name: 'DateTimeRangePicker',
            props: ['start', 'end', 'startErrorMessages', 'endErrorMessages'],
            template: '<div />',
          },
          ReportPeriodSelector: {
            emits: ['update:period', 'update:selection'],
            name: 'ReportPeriodSelector',
            props: ['year', 'quarter'],
            template: '<div />',
          },
        },
      },
      props: { modelValue },
    });
  }

  function picker(): VueWrapper<StubInstance> {
    return wrapper.findComponent<StubInstance>({ name: 'DateTimeRangePicker' });
  }

  function messages(prop: 'startErrorMessages' | 'endErrorMessages'): string[] {
    const value: unknown = picker().props(prop);
    assert(Array.isArray(value));
    return value.map(String);
  }

  function lastValid(): boolean | undefined {
    return wrapper.emitted<[boolean]>('update:valid')?.at(-1)?.[0];
  }

  async function selectCustom(): Promise<void> {
    set(period, { quarter: Quarter.Q1, year: 'custom' });
    await vi.advanceTimersToNextTimerAsync();
  }

  it('should hide the range picker outside the custom period', async () => {
    wrapper = createWrapper();
    await vi.advanceTimersToNextTimerAsync();

    expect(picker().exists()).toBe(false);
  });

  it('should report a preset period as valid even with no start date', async () => {
    wrapper = createWrapper({ end: 1700000000, start: undefined });
    await vi.advanceTimersToNextTimerAsync();

    expect(lastValid()).toBe(true);
  });

  it('should report a custom period with no start date as invalid', async () => {
    wrapper = createWrapper({ end: 1700000000, start: undefined });
    await selectCustom();

    expect(lastValid()).toBe(false);
  });

  it('should report a custom period with no end date as invalid', async () => {
    wrapper = createWrapper();
    await selectCustom();

    // The picker allows an empty end date, so it is reached the way the app reaches it rather
    // than by seeding a value the model type does not admit.
    picker().vm.$emit('update:end', undefined);
    await vi.advanceTimersToNextTimerAsync();

    expect(lastValid()).toBe(false);
  });

  it('should report a fully filled custom period as valid', async () => {
    wrapper = createWrapper();
    await selectCustom();

    expect(lastValid()).toBe(true);
  });

  it('should accept a zero start date as present', async () => {
    wrapper = createWrapper({ end: 1700000000, start: 0 });
    await selectCustom();

    expect(lastValid()).toBe(true);
  });

  it('should never render a message on either date field', async () => {
    wrapper = createWrapper();
    await selectCustom();

    // Edit both fields into an invalid state. Under $autoDirty that is exactly what makes a
    // message appear; here it must not, because the picker is configured with it off and nothing
    // touches the fields. These two messages have never been reachable.
    picker().vm.$emit('update:start', undefined);
    picker().vm.$emit('update:end', undefined);
    await vi.advanceTimersToNextTimerAsync();

    expect(lastValid()).toBe(false);
    expect(messages('startErrorMessages')).toEqual([]);
    expect(messages('endErrorMessages')).toEqual([]);
  });

  it('should blank the range when a custom period is picked', async () => {
    wrapper = createWrapper();
    await vi.advanceTimersToNextTimerAsync();

    wrapper.findComponent<StubInstance>({ name: 'ReportPeriodSelector' }).vm.$emit('update:period', null);
    await vi.advanceTimersToNextTimerAsync();

    expect(wrapper.emitted<[Range]>('update:modelValue')?.at(-1)?.[0]).toEqual({
      end: dayjs().unix(),
      start: undefined,
    });
  });

  it('should clamp a preset period that reaches past now', async () => {
    wrapper = createWrapper();
    await vi.advanceTimersToNextTimerAsync();

    const future = dayjs().unix() + 10_000;
    wrapper.findComponent<StubInstance>({ name: 'ReportPeriodSelector' })
      .vm
      .$emit('update:period', { end: future, start: 1600000000 });
    await vi.advanceTimersToNextTimerAsync();

    expect(wrapper.emitted<[Range]>('update:modelValue')?.at(-1)?.[0]).toEqual({
      end: dayjs().unix(),
      start: 1600000000,
    });
  });

  it('should reset the range before persisting a switch to custom', async () => {
    wrapper = createWrapper();
    await vi.advanceTimersToNextTimerAsync();

    const selection = { quarter: Quarter.Q1, year: 'custom' };
    wrapper.findComponent<StubInstance>({ name: 'ReportPeriodSelector' }).vm.$emit('update:selection', selection);
    await vi.advanceTimersToNextTimerAsync();

    expect(wrapper.emitted<[Range]>('update:modelValue')?.at(-1)?.[0]).toEqual({
      end: dayjs().unix(),
      start: undefined,
    });
    expect(updateFrontendSetting).toHaveBeenCalledWith({ profitLossReportPeriod: selection });
  });
});
