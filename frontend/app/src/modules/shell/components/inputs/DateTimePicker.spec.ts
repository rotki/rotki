import { type ComponentMountingOptions, mount, type VueWrapper } from '@vue/test-utils';
import dayjs from 'dayjs';
import { createPinia, type Pinia, setActivePinia } from 'pinia';
import { afterEach, beforeAll, beforeEach, describe, expect, it, vi } from 'vitest';
import { defineComponent, h, type VNode } from 'vue';
import { setupDayjs } from '@/modules/core/common/data/date';
import DateTimePicker from '@/modules/shell/components/inputs/DateTimePicker.vue';

/** The quick-option buttons, in the order the picker renders them. */
const QuickOption = {
  DAY_BEFORE: 0,
  WEEK_BEFORE: 1,
  MONTH_BEFORE: 2,
  NINETY_DAYS_BEFORE: 3,
  SIX_MONTHS_BEFORE: 4,
  YEAR_BEFORE: 5,
} as const;

function getEmittedValue(wrapper: VueWrapper, event: string, callIndex: number): number {
  const emitted = wrapper.emitted(event);
  expect(emitted).toBeDefined();
  const value = emitted![callIndex][0];
  expect(value).toEqual(expect.any(Number));
  return Number(value);
}

const RuiDateTimePickerStub = defineComponent({
  emits: ['update:modelValue'],
  name: 'RuiDateTimePicker',
  props: {
    modelValue: {
      required: true,
      type: Number,
    },
  },
  setup(props, { emit, slots }): () => VNode {
    return (): VNode => h('div', { class: 'rui-date-time-picker' }, [
      h('input', {
        onInput: (e: Event) => {
          if (e.target instanceof HTMLInputElement)
            emit('update:modelValue', Number(e.target.value));
        },
        value: props.modelValue,
      }),
      slots['menu-content']?.(),
    ]);
  },
});

describe('components/inputs/DateTimePicker.vue', () => {
  let wrapper: VueWrapper<InstanceType<typeof DateTimePicker>>;
  let pinia: Pinia;

  beforeAll(() => {
    setupDayjs();
    pinia = createPinia();
    setActivePinia(pinia);
  });

  beforeEach(() => {
    vi.useFakeTimers();
  });

  afterEach(() => {
    wrapper.unmount();
    vi.useRealTimers();
  });

  const createWrapper = (
    options: ComponentMountingOptions<typeof DateTimePicker> = {
      props: {
        modelValue: dayjs().unix(),
      },
    },
  ): VueWrapper<InstanceType<typeof DateTimePicker>> =>
    mount(DateTimePicker, {
      global: {
        plugins: [pinia],
        stubs: {
          RuiButton: {
            template: '<button @click="$emit(\'click\')"><slot /></button>',
          },
          RuiDateTimePicker: RuiDateTimePickerStub,
          RuiIcon: true,
        },
      },
      ...options,
    });

  describe('quick options', () => {
    it('should render quick option buttons', () => {
      wrapper = createWrapper();

      const quickOptionButtons = wrapper.findAll('.border-t button');
      expect(quickOptionButtons).toHaveLength(6);
    });

    it('should subtract time from current model value when quick option is clicked (unix seconds)', async () => {
      const initialDate = dayjs('2024-06-15T12:00:00');
      const initialUnix = initialDate.unix();

      wrapper = createWrapper({
        props: {
          modelValue: initialUnix,
        },
      });

      const quickOptionButtons = wrapper.findAll('.border-t button');
      const yearBeforeButton = quickOptionButtons[QuickOption.YEAR_BEFORE];

      // First click - should subtract 1 year from initial date
      await yearBeforeButton.trigger('click');
      await vi.advanceTimersToNextTimerAsync();

      const firstValue = getEmittedValue(wrapper, 'update:modelValue', 0);

      const expectedFirstValue = initialDate.subtract(1, 'year').unix();
      expect(firstValue).toBe(expectedFirstValue);

      await wrapper.setProps({ modelValue: firstValue });

      // Second click - should subtract another year from the new value (not from now)
      await yearBeforeButton.trigger('click');
      await vi.advanceTimersToNextTimerAsync();

      const secondValue = getEmittedValue(wrapper, 'update:modelValue', 1);

      const expectedSecondValue = initialDate.subtract(2, 'year').unix();
      expect(secondValue).toBe(expectedSecondValue);
    });

    it('should subtract time from current model value when quick option is clicked (milliseconds)', async () => {
      const initialDate = dayjs('2024-06-15T12:00:00');
      const initialMs = initialDate.valueOf();

      wrapper = createWrapper({
        props: {
          accuracy: 'millisecond',
          modelValue: initialMs,
        },
      });

      const quickOptionButtons = wrapper.findAll('.border-t button');
      const monthBeforeButton = quickOptionButtons[QuickOption.MONTH_BEFORE];

      // First click - should subtract 1 month from initial date
      await monthBeforeButton.trigger('click');
      await vi.advanceTimersToNextTimerAsync();

      const firstValue = getEmittedValue(wrapper, 'update:modelValue', 0);

      const expectedFirstValue = initialDate.subtract(1, 'month').valueOf();
      expect(firstValue).toBe(expectedFirstValue);

      await wrapper.setProps({ modelValue: firstValue });

      // Second click - should subtract another month from the new value
      await monthBeforeButton.trigger('click');
      await vi.advanceTimersToNextTimerAsync();

      const secondValue = getEmittedValue(wrapper, 'update:modelValue', 1);

      const expectedSecondValue = initialDate.subtract(2, 'month').valueOf();
      expect(secondValue).toBe(expectedSecondValue);
    });

    it('should handle day subtraction correctly', async () => {
      const initialDate = dayjs('2024-06-15T12:00:00');
      const initialUnix = initialDate.unix();

      wrapper = createWrapper({
        props: {
          modelValue: initialUnix,
        },
      });

      const quickOptionButtons = wrapper.findAll('.border-t button');
      const yesterdayButton = quickOptionButtons[QuickOption.DAY_BEFORE];

      await yesterdayButton.trigger('click');
      await vi.advanceTimersToNextTimerAsync();

      const emittedValue = getEmittedValue(wrapper, 'update:modelValue', 0);

      const expectedValue = initialDate.subtract(1, 'day').unix();
      expect(emittedValue).toBe(expectedValue);
    });

    it('should handle week subtraction correctly', async () => {
      const initialDate = dayjs('2024-06-15T12:00:00');
      const initialUnix = initialDate.unix();

      wrapper = createWrapper({
        props: {
          modelValue: initialUnix,
        },
      });

      const quickOptionButtons = wrapper.findAll('.border-t button');
      const weekBeforeButton = quickOptionButtons[QuickOption.WEEK_BEFORE];

      await weekBeforeButton.trigger('click');
      await vi.advanceTimersToNextTimerAsync();

      const emittedValue = getEmittedValue(wrapper, 'update:modelValue', 0);

      const expectedValue = initialDate.subtract(1, 'week').unix();
      expect(emittedValue).toBe(expectedValue);
    });

    it('should handle 90 days subtraction correctly', async () => {
      const initialDate = dayjs('2024-06-15T12:00:00');
      const initialUnix = initialDate.unix();

      wrapper = createWrapper({
        props: {
          modelValue: initialUnix,
        },
      });

      const quickOptionButtons = wrapper.findAll('.border-t button');
      const ninetyDaysButton = quickOptionButtons[QuickOption.NINETY_DAYS_BEFORE];

      await ninetyDaysButton.trigger('click');
      await vi.advanceTimersToNextTimerAsync();

      const emittedValue = getEmittedValue(wrapper, 'update:modelValue', 0);

      const expectedValue = initialDate.subtract(90, 'day').unix();
      expect(emittedValue).toBe(expectedValue);
    });

    it('should handle 6 months subtraction correctly', async () => {
      const initialDate = dayjs('2024-06-15T12:00:00');
      const initialUnix = initialDate.unix();

      wrapper = createWrapper({
        props: {
          modelValue: initialUnix,
        },
      });

      const quickOptionButtons = wrapper.findAll('.border-t button');
      const sixMonthsButton = quickOptionButtons[QuickOption.SIX_MONTHS_BEFORE];

      await sixMonthsButton.trigger('click');
      await vi.advanceTimersToNextTimerAsync();

      const emittedValue = getEmittedValue(wrapper, 'update:modelValue', 0);

      const expectedValue = initialDate.subtract(6, 'month').unix();
      expect(emittedValue).toBe(expectedValue);
    });
  });
});
