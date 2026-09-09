import { TimeFramePeriod, TimeFramePersist, type TimeFrameSetting } from '@rotki/common';
import { flushPromises, mount, type VueWrapper } from '@vue/test-utils';
import { beforeEach, describe, expect, it, type Mock, vi } from 'vitest';
import TimeFrameSettings from '@/modules/settings/general/TimeFrameSettings.vue';
import { createRuiPlugin } from '@/plugins/rui';

const { premium, updateFrontendSetting, updateSession } = await vi.hoisted(async () => {
  const { ref } = await import('vue');
  return {
    premium: ref<boolean>(true),
    updateFrontendSetting: vi.fn(async () => ({ success: true })),
    updateSession: vi.fn(),
  };
});

vi.mock('@/modules/premium/use-premium', () => ({
  usePremium: (): typeof premium => premium,
}));

vi.mock('@/modules/settings/use-settings-operations', () => ({
  useSettingsOperations: (): { updateFrontendSetting: Mock } => ({ updateFrontendSetting }),
}));

vi.mock('@/modules/settings/settings-repo', () => ({
  useSettingsRepo: (): { updateSession: Mock } => ({ updateSession }),
}));

const ALL = Object.values(TimeFramePeriod);

function createWrapper(props: Record<string, unknown> = {}): VueWrapper<any> {
  return mount(TimeFrameSettings, {
    global: {
      plugins: [createRuiPlugin({})],
      stubs: { PremiumLock: true },
    },
    props: {
      currentSessionTimeframe: TimeFramePeriod.WEEK,
      message: { error: '', success: '' },
      value: TimeFramePeriod.WEEK,
      visibleTimeframes: [TimeFramePeriod.WEEK, TimeFramePeriod.MONTH, TimeFramePeriod.YEAR],
      ...props,
    },
  });
}

/** The chips the user can pick from, in the order they render. */
function chips(wrapper: VueWrapper<any>): VueWrapper<any>[] {
  return wrapper.findAllComponents({ name: 'RuiChip' });
}

/**
 * The chip's own label.
 *
 * @remarks
 * `RuiIcon` is globally stubbed to render its name, so a closeable chip's text carries a trailing
 * `lu-…` that is not part of the label.
 */
function label(chip: VueWrapper<any>): string {
  return chip.text().replace(/lu-[\w-]+$/, '');
}

function chipFor(wrapper: VueWrapper<any>, timeframe: TimeFrameSetting): VueWrapper<any> | undefined {
  return chips(wrapper).find(chip => label(chip) === timeframe);
}

function lastVisibleChange(wrapper: VueWrapper<any>): TimeFrameSetting[] | undefined {
  return wrapper.emitted<[TimeFrameSetting[]]>('visible-timeframes-change')?.at(-1)?.[0];
}

describe('timeFrameSettings', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    set(premium, true);
  });

  it('should offer remember alongside the visible timeframes', () => {
    const wrapper = createWrapper();

    expect(chips(wrapper)[0].text()).toBe(TimeFramePersist.REMEMBER);
  });

  it('should offer the rest as inactive', () => {
    const wrapper = createWrapper({ visibleTimeframes: [TimeFramePeriod.WEEK] });

    const shown = chips(wrapper).map(chip => label(chip));

    for (const timeframe of ALL.filter(period => period !== TimeFramePeriod.WEEK))
      expect(shown).toContain(timeframe);
  });

  /** The list is re-sorted into the period order, longest first, rather than order of adding. */
  describe('adding a timeframe back', () => {
    it('should put a longer period in front rather than appending it', async () => {
      const wrapper = createWrapper({ visibleTimeframes: [TimeFramePeriod.WEEK] });

      await chipFor(wrapper, TimeFramePeriod.YEAR)?.vm.$emit('click');

      expect(lastVisibleChange(wrapper)).toEqual([TimeFramePeriod.YEAR, TimeFramePeriod.WEEK]);
    });

    it('should place a middle period between the two it belongs between', async () => {
      const wrapper = createWrapper({ visibleTimeframes: [TimeFramePeriod.YEAR, TimeFramePeriod.WEEK] });

      await chipFor(wrapper, TimeFramePeriod.MONTH)?.vm.$emit('click');

      expect(lastVisibleChange(wrapper))
        .toEqual([TimeFramePeriod.YEAR, TimeFramePeriod.MONTH, TimeFramePeriod.WEEK]);
    });
  });

  describe('removing a timeframe', () => {
    it('should drop it from the visible list', async () => {
      const wrapper = createWrapper();

      await chipFor(wrapper, TimeFramePeriod.MONTH)?.vm.$emit('click:close');

      expect(lastVisibleChange(wrapper)).toEqual([TimeFramePeriod.YEAR, TimeFramePeriod.WEEK]);
    });

    /** The selected timeframe cannot stay selected once it is no longer on offer. */
    it('should fall back to remember when the selected one is removed', async () => {
      const wrapper = createWrapper({ value: TimeFramePeriod.MONTH });

      await chipFor(wrapper, TimeFramePeriod.MONTH)?.vm.$emit('click:close');

      expect(wrapper.emitted<[TimeFrameSetting]>('timeframe-change')?.at(-1)?.[0])
        .toBe(TimeFramePersist.REMEMBER);
    });

    it('should leave the selection alone when another one is removed', async () => {
      const wrapper = createWrapper({ value: TimeFramePeriod.WEEK });

      await chipFor(wrapper, TimeFramePeriod.MONTH)?.vm.$emit('click:close');

      expect(wrapper.emitted('timeframe-change')).toBeUndefined();
    });

    /**
     * The session is showing that timeframe right now, so it is moved to the longest one still on
     * offer and remembered, rather than left pointing at something that is gone.
     */
    it('should move the session on when its own timeframe is removed', async () => {
      const wrapper = createWrapper({ currentSessionTimeframe: TimeFramePeriod.WEEK });

      await chipFor(wrapper, TimeFramePeriod.WEEK)?.vm.$emit('click:close');
      await flushPromises();

      expect(updateSession).toHaveBeenCalledWith({ timeframe: TimeFramePeriod.YEAR });
      expect(updateFrontendSetting).toHaveBeenCalledWith({ lastKnownTimeframe: TimeFramePeriod.YEAR });
    });

    it('should leave the session alone when another timeframe is removed', async () => {
      const wrapper = createWrapper({ currentSessionTimeframe: TimeFramePeriod.WEEK });

      await chipFor(wrapper, TimeFramePeriod.MONTH)?.vm.$emit('click:close');
      await flushPromises();

      expect(updateSession).not.toHaveBeenCalled();
      expect(updateFrontendSetting).not.toHaveBeenCalled();
    });

    it('should refuse to remove the last one left', () => {
      const wrapper = createWrapper({ visibleTimeframes: [TimeFramePeriod.WEEK] });

      expect(chipFor(wrapper, TimeFramePeriod.WEEK)?.props('closeable')).toBe(false);
    });

    /** Remember is not a timeframe of its own, so it is never removable. */
    it('should refuse to remove remember', () => {
      const wrapper = createWrapper();

      expect(chipFor(wrapper, TimeFramePersist.REMEMBER)?.props('closeable')).toBe(false);
    });
  });

  /** The longer ranges are a premium feature, so a free account sees them but cannot pick them. */
  describe('with premium', () => {
    it('should leave the timeframes premium pays for usable', () => {
      const wrapper = createWrapper({ visibleTimeframes: ALL });

      expect(chipFor(wrapper, TimeFramePeriod.ALL)?.props('disabled')).toBe(false);
    });
  });

  describe('without premium', () => {
    beforeEach(() => {
      set(premium, false);
    });

    it('should disable the timeframes premium pays for', () => {
      const wrapper = createWrapper({ visibleTimeframes: ALL });

      expect(chipFor(wrapper, TimeFramePeriod.ALL)?.props('disabled')).toBe(true);
    });

    it('should leave the short ranges usable', () => {
      const wrapper = createWrapper({ visibleTimeframes: ALL });

      expect(chipFor(wrapper, TimeFramePeriod.WEEK)?.props('disabled')).toBe(false);
    });

    it('should keep remember usable', () => {
      const wrapper = createWrapper();

      expect(chipFor(wrapper, TimeFramePersist.REMEMBER)?.props('disabled')).toBe(false);
    });

    it('should offer the upgrade prompt', () => {
      expect(createWrapper().findComponent({ name: 'PremiumLock' }).exists()).toBe(true);
    });

    it('should not prompt a premium account', () => {
      set(premium, true);

      expect(createWrapper().findComponent({ name: 'PremiumLock' }).exists()).toBe(false);
    });
  });

  describe('the status line', () => {
    it('should show a success message', () => {
      const wrapper = createWrapper({ message: { error: '', success: 'saved' } });

      expect(wrapper.text()).toContain('saved');
    });

    it('should show an error message', () => {
      const wrapper = createWrapper({ message: { error: 'nope', success: '' } });

      expect(wrapper.text()).toContain('nope');
    });
  });
});
