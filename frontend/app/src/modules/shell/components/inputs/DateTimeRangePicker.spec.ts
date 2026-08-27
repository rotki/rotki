import { type ComponentMountingOptions, mount, type VueWrapper } from '@vue/test-utils';
import dayjs from 'dayjs';
import { createPinia, type Pinia, setActivePinia } from 'pinia';
import { afterEach, beforeAll, beforeEach, describe, expect, it, vi } from 'vitest';
import { defineComponent, h, type VNode } from 'vue';
import { setupDayjs } from '@/modules/core/common/data/date';
import DateTimeRangePicker from '@/modules/shell/components/inputs/DateTimeRangePicker.vue';

const RuiDateTimePickerStub = defineComponent({
  emits: ['update:modelValue'],
  name: 'RuiDateTimePicker',
  props: {
    modelValue: {
      default: undefined,
      required: false,
      type: Number,
    },
  },
  setup(_, { slots }): () => VNode {
    return (): VNode => h('div', { class: 'rui-date-time-picker' }, [
      slots['menu-content']?.(),
    ]);
  },
});

const PICKERS = 2;
const QUICK_OPTIONS_PER_PICKER = 7;
const LAST_12_HOURS = 0;

function isSingleNumberCall(value: unknown[]): value is [number] {
  return value.length === 1 && typeof value[0] === 'number';
}

function firstNumberArg(calls: unknown[][] | undefined, callIndex: number): number {
  expect(calls).toBeDefined();
  if (calls === undefined) {
    throw new Error('emitted() returned undefined');
  }
  const call = calls[callIndex];
  expect(call).toBeDefined();
  expect(isSingleNumberCall(call)).toBe(true);
  if (!isSingleNumberCall(call)) {
    throw new Error(`emitted call ${callIndex} has unexpected shape`);
  }
  return call[0];
}

describe('components/inputs/DateTimeRangePicker.vue', () => {
  let wrapper: VueWrapper<InstanceType<typeof DateTimeRangePicker>>;
  let pinia: Pinia;

  beforeAll((): void => {
    setupDayjs();
  });

  beforeEach((): void => {
    pinia = createPinia();
    setActivePinia(pinia);
    vi.useFakeTimers();
  });

  afterEach((): void => {
    wrapper?.unmount();
    vi.useRealTimers();
  });

  function createWrapper(
    options: ComponentMountingOptions<typeof DateTimeRangePicker> = {
      props: {
        end: dayjs().unix(),
        start: undefined,
      },
    },
  ): VueWrapper<InstanceType<typeof DateTimeRangePicker>> {
    return mount(DateTimeRangePicker, {
      global: {
        plugins: [pinia],
        stubs: {
          RuiButton: {
            template: '<button class="quick-option" @click="$emit(\'click\')"><slot /></button>',
          },
          RuiDateTimePicker: RuiDateTimePickerStub,
          RuiIcon: true,
        },
      },
      ...options,
    });
  }

  async function clickQuickOption(
    picker: VueWrapper<InstanceType<typeof DateTimeRangePicker>>,
    index: number,
  ): Promise<void> {
    await picker.findAll('button.quick-option')[index].trigger('click');
    await nextTick();
  }

  describe('quick options', (): void => {
    it('should render all seven quick-option buttons inside both pickers', (): void => {
      wrapper = createWrapper();

      const quickOptionButtons = wrapper.findAll('button.quick-option');
      expect(quickOptionButtons).toHaveLength(PICKERS * QUICK_OPTIONS_PER_PICKER);
    });

    it('should update end before start when a stale end is held with no start, so the start picker never validates against the stale max date', async (): Promise<void> => {
      const now = dayjs('2026-04-23T14:58:00');
      vi.setSystemTime(now.toDate());

      wrapper = createWrapper({
        props: {
          end: dayjs('2024-06-30T23:59:59').unix(),
          start: undefined,
        },
      });

      await clickQuickOption(wrapper, LAST_12_HOURS);

      const endEmits = wrapper.emitted('update:end');
      const startEmits = wrapper.emitted('update:start');
      expect(endEmits).toHaveLength(1);
      expect(startEmits).toHaveLength(1);

      expect(firstNumberArg(endEmits, 0)).toBe(now.unix());
      expect(firstNumberArg(startEmits, 0)).toBe(now.subtract(12, 'hour').unix());
    });

    it('should compute each preset from the current timestamp', async (): Promise<void> => {
      const now = dayjs('2026-04-23T14:58:00');
      vi.setSystemTime(now.toDate());

      wrapper = createWrapper({
        props: {
          end: now.unix(),
          start: undefined,
        },
      });

      const cases: Array<{ index: number; expectedStart: number }> = [
        { expectedStart: now.subtract(12, 'hour').unix(), index: 0 },
        { expectedStart: now.subtract(24, 'hour').unix(), index: 1 },
        { expectedStart: now.subtract(7, 'day').unix(), index: 2 },
        { expectedStart: now.subtract(1, 'month').unix(), index: 3 },
        { expectedStart: now.subtract(90, 'day').unix(), index: 4 },
        { expectedStart: now.subtract(180, 'day').unix(), index: 5 },
        { expectedStart: now.subtract(1, 'year').unix(), index: 6 },
      ];

      for (const { index } of cases)
        await clickQuickOption(wrapper, index);

      const startEmits = wrapper.emitted('update:start');
      expect(startEmits).toHaveLength(cases.length);
      cases.forEach(({ expectedStart }, index: number): void => {
        expect(firstNumberArg(startEmits, index)).toBe(expectedStart);
      });
    });
  });
});
