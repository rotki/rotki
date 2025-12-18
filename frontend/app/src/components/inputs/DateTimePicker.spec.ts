import { type ComponentMountingOptions, mount, type VueWrapper } from '@vue/test-utils';
import dayjs from 'dayjs';
import { createPinia, type Pinia, setActivePinia } from 'pinia';
import { afterEach, beforeAll, beforeEach, describe, expect, it, vi } from 'vitest';
import { defineComponent, h, type VNode } from 'vue';
import DateTimePicker from '@/components/inputs/DateTimePicker.vue';
import { setupDayjs } from '@/utils/date';

// Mock RuiDateTimePicker to render the menu-content slot
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
        onInput: (e: Event) => emit('update:modelValue', Number((e.target as HTMLInputElement).value)),
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
      expect(quickOptionButtons.length).toBe(6);
    });

    it('should subtract time from current model value when quick option is clicked (unix seconds)', async () => {
      const initialDate = dayjs('2024-06-15T12:00:00');
      const initialUnix = initialDate.unix();

      wrapper = createWrapper({
        props: {
          modelValue: initialUnix,
        },
      });

      // Find the "1 year before" button (last quick option)
      const quickOptionButtons = wrapper.findAll('.border-t button');
      const yearBeforeButton = quickOptionButtons[5];

      // First click - should subtract 1 year from initial date
      await yearBeforeButton.trigger('click');
      await vi.advanceTimersToNextTimerAsync();

      const firstEmit = wrapper.emitted('update:modelValue');
      expect(firstEmit).toBeTruthy();
      const firstValue = firstEmit![0][0] as number;

      const expectedFirstValue = initialDate.subtract(1, 'year').unix();
      expect(firstValue).toBe(expectedFirstValue);

      // Update the wrapper with new value to simulate v-model
      await wrapper.setProps({ modelValue: firstValue });

      // Second click - should subtract another year from the new value (not from now)
      await yearBeforeButton.trigger('click');
      await vi.advanceTimersToNextTimerAsync();

      const secondEmit = wrapper.emitted('update:modelValue');
      expect(secondEmit).toBeTruthy();
      const secondValue = secondEmit![1][0] as number;

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

      // Find the "1 month before" button
      const quickOptionButtons = wrapper.findAll('.border-t button');
      const monthBeforeButton = quickOptionButtons[2];

      // First click - should subtract 1 month from initial date
      await monthBeforeButton.trigger('click');
      await vi.advanceTimersToNextTimerAsync();

      const firstEmit = wrapper.emitted('update:modelValue');
      expect(firstEmit).toBeTruthy();
      const firstValue = firstEmit![0][0] as number;

      const expectedFirstValue = initialDate.subtract(1, 'month').valueOf();
      expect(firstValue).toBe(expectedFirstValue);

      // Update the wrapper with new value to simulate v-model
      await wrapper.setProps({ modelValue: firstValue });

      // Second click - should subtract another month from the new value
      await monthBeforeButton.trigger('click');
      await vi.advanceTimersToNextTimerAsync();

      const secondEmit = wrapper.emitted('update:modelValue');
      expect(secondEmit).toBeTruthy();
      const secondValue = secondEmit![1][0] as number;

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

      // Find the "1 day before" button (first quick option)
      const quickOptionButtons = wrapper.findAll('.border-t button');
      const yesterdayButton = quickOptionButtons[0];

      await yesterdayButton.trigger('click');
      await vi.advanceTimersToNextTimerAsync();

      const emittedEvents = wrapper.emitted('update:modelValue');
      expect(emittedEvents).toBeTruthy();
      const emittedValue = emittedEvents![0][0] as number;

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

      // Find the "week before" button (second quick option)
      const quickOptionButtons = wrapper.findAll('.border-t button');
      const weekBeforeButton = quickOptionButtons[1];

      await weekBeforeButton.trigger('click');
      await vi.advanceTimersToNextTimerAsync();

      const emittedEvents = wrapper.emitted('update:modelValue');
      expect(emittedEvents).toBeTruthy();
      const emittedValue = emittedEvents![0][0] as number;

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

      // Find the "90 days before" button (fourth quick option)
      const quickOptionButtons = wrapper.findAll('.border-t button');
      const ninetyDaysButton = quickOptionButtons[3];

      await ninetyDaysButton.trigger('click');
      await vi.advanceTimersToNextTimerAsync();

      const emittedEvents = wrapper.emitted('update:modelValue');
      expect(emittedEvents).toBeTruthy();
      const emittedValue = emittedEvents![0][0] as number;

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

      // Find the "6 months before" button (fifth quick option)
      const quickOptionButtons = wrapper.findAll('.border-t button');
      const sixMonthsButton = quickOptionButtons[4];

      await sixMonthsButton.trigger('click');
      await vi.advanceTimersToNextTimerAsync();

      const emittedEvents = wrapper.emitted('update:modelValue');
      expect(emittedEvents).toBeTruthy();
      const emittedValue = emittedEvents![0][0] as number;

      const expectedValue = initialDate.subtract(6, 'month').unix();
      expect(emittedValue).toBe(expectedValue);
    });
  });
});
