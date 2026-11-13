import { libraryDefaults } from '@test/utils/provide-defaults';
import { flushPromises, mount, type VueWrapper } from '@vue/test-utils';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import SmallValueEventsSetting from '@/modules/settings/general/SmallValueEventsSetting.vue';
import { useSettingsRepo } from '@/modules/settings/settings-repo';

const updateFrontendSetting = vi.hoisted(() => vi.fn().mockResolvedValue({ success: true }));

vi.mock('@/modules/settings/use-settings-operations', () => ({
  useSettingsOperations: (): Record<string, ReturnType<typeof vi.fn>> => ({
    applyFrontendSettingLocal: vi.fn(),
    enableModule: vi.fn(),
    update: vi.fn(),
    updateFrontendSetting,
  }),
}));

describe('smallValueEventsSetting', () => {
  function createWrapper(): VueWrapper<InstanceType<typeof SmallValueEventsSetting>> {
    const pinia = createPinia();
    setActivePinia(pinia);
    return mount(SmallValueEventsSetting, {
      global: { plugins: [pinia] },
      provide: libraryDefaults,
    });
  }

  function thresholdInput(wrapper: VueWrapper): HTMLInputElement {
    return wrapper.find<HTMLInputElement>('[data-testid=small-value-events-threshold] input').element;
  }

  beforeEach(() => {
    vi.useFakeTimers();
    updateFrontendSetting.mockClear();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it('should show the default threshold, locked while de-emphasizing is off', async () => {
    const wrapper = createWrapper();
    await flushPromises();

    expect(thresholdInput(wrapper).value).toBe('1');
    expect(thresholdInput(wrapper).disabled).toBe(true);
  });

  it('should unlock the threshold once de-emphasizing is on', async () => {
    const wrapper = createWrapper();
    useSettingsRepo().updateFrontend({ deemphasizeSmallValueEvents: true });
    await flushPromises();

    expect(thresholdInput(wrapper).disabled).toBe(false);
  });

  it('should persist turning de-emphasizing on', async () => {
    const wrapper = createWrapper();
    await flushPromises();

    await wrapper.find('[data-testid=small-value-events-toggle] input').setValue(true);
    await flushPromises();

    expect(updateFrontendSetting).toHaveBeenCalledWith({ deemphasizeSmallValueEvents: true });
  });

  it('should persist a fractional threshold without rounding it', async () => {
    const wrapper = createWrapper();
    useSettingsRepo().updateFrontend({ deemphasizeSmallValueEvents: true });
    await flushPromises();

    await wrapper.find('[data-testid=small-value-events-threshold] input').setValue('0.25');
    await vi.runAllTimersAsync();
    await flushPromises();

    expect(updateFrontendSetting).toHaveBeenCalledWith({ smallValueEventThreshold: 0.25 });
  });
});
