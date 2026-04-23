import { type ComponentMountingOptions, mount, type VueWrapper } from '@vue/test-utils';
import dayjs from 'dayjs';
import { createPinia, type Pinia, setActivePinia } from 'pinia';
import { afterEach, beforeAll, beforeEach, describe, expect, it, vi } from 'vitest';
import { defineComponent, h, type VNode } from 'vue';
import { setupDayjs } from '@/modules/core/common/data/date';
import DateTimeRangePicker from '@/modules/shell/components/inputs/DateTimeRangePicker.vue';

// Stub RuiDateTimePicker so we can render the `menu-content` slot (where
// the quick-option buttons live) without pulling in the full picker.
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

// Vue Test Utils types `emitted()` as `unknown[][] | undefined`. Narrow it
// to the `[number]`-per-call shape our picker emits before touching values.
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

  describe('quick options', (): void => {
    it('should render all seven quick-option buttons inside both pickers', (): void => {
      wrapper = createWrapper();

      // Each picker renders the same DefineQuickOptions template, so the
      // button count is 2 × 7 = 14. The component re-uses the template to
      // keep start/end menus in sync without duplicating the button list.
      const quickOptionButtons = wrapper.findAll('button.quick-option');
      expect(quickOptionButtons).toHaveLength(14);
    });

    it('should update end before start (regression: stale max-date error)', async (): Promise<void> => {
      // Regression for the bug where clicking a quick-option right after
      // switching to Custom (from a past year/quarter) left the start
      // picker latched on the old max-date error ("Date cannot be after
      // 6/30/2024" or similar). The fix sets `end` first so the max-date
      // constraint on start widens before start is written.
      const now = dayjs('2026-04-23T14:58:00');
      vi.setSystemTime(now.toDate());

      wrapper = createWrapper({
        props: {
          // Mirror the "arrived at Custom from a past year/quarter" state —
          // end is stuck at the previous period's end until onChanged
          // clears it. In the buggy path, setting start first would
          // trigger start > end validation.
          end: dayjs('2024-06-30T23:59:59').unix(),
          start: undefined,
        },
      });

      // Click the first quick option ("Last 12 hours") in the start picker.
      const buttons = wrapper.findAll('button.quick-option');
      await buttons[0].trigger('click');
      await vi.advanceTimersToNextTimerAsync();

      // Both update events should have fired exactly once each.
      const endEmits = wrapper.emitted('update:end');
      const startEmits = wrapper.emitted('update:start');
      expect(endEmits).toHaveLength(1);
      expect(startEmits).toHaveLength(1);

      // End must be emitted first — that's what protects the start picker
      // from validating against a stale max-date.
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

      const buttons = wrapper.findAll('button.quick-option');

      // Button layout (order matches `quickOptions`): 12h, 24h, 7d, 1m,
      // 90d, 6m, 1y — then the same seven repeated for the end picker.
      const cases: Array<{ index: number; expectedStart: number }> = [
        { expectedStart: now.subtract(12, 'hour').unix(), index: 0 },
        { expectedStart: now.subtract(24, 'hour').unix(), index: 1 },
        { expectedStart: now.subtract(7, 'day').unix(), index: 2 },
        { expectedStart: now.subtract(1, 'month').unix(), index: 3 },
        { expectedStart: now.subtract(90, 'day').unix(), index: 4 },
        { expectedStart: now.subtract(180, 'day').unix(), index: 5 },
        { expectedStart: now.subtract(1, 'year').unix(), index: 6 },
      ];

      for (const { index } of cases) {
        await buttons[index].trigger('click');
        await vi.advanceTimersToNextTimerAsync();
      }

      const startEmits = wrapper.emitted('update:start');
      expect(startEmits).toHaveLength(cases.length);
      cases.forEach(({ expectedStart }, index: number): void => {
        expect(firstNumberArg(startEmits, index)).toBe(expectedStart);
      });
    });
  });
});
