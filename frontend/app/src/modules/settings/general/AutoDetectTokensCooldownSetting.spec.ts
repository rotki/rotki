import { libraryDefaults } from '@test/utils/provide-defaults';
import { flushPromises, mount, type VueWrapper } from '@vue/test-utils';
import { describe, expect, it, vi } from 'vitest';
import AutoDetectTokensCooldownSetting from '@/modules/settings/general/AutoDetectTokensCooldownSetting.vue';
import { useSettingsRepo } from '@/modules/settings/settings-repo';

vi.mock('@/modules/settings/use-settings-operations', () => ({
  useSettingsOperations: (): Record<string, ReturnType<typeof vi.fn>> => ({
    applyFrontendSettingLocal: vi.fn(),
    enableModule: vi.fn(),
    setKrakenAccountType: vi.fn(),
    update: vi.fn(),
    updateFrontendSetting: vi.fn().mockResolvedValue({ success: true }),
  }),
}));

describe('autoDetectTokensCooldownSetting', () => {
  let wrapper: VueWrapper<InstanceType<typeof AutoDetectTokensCooldownSetting>>;

  function createWrapper(): VueWrapper<InstanceType<typeof AutoDetectTokensCooldownSetting>> {
    const pinia = createPinia();
    setActivePinia(pinia);
    return mount(AutoDetectTokensCooldownSetting, {
      global: { plugins: [pinia] },
      provide: libraryDefaults,
    });
  }

  it('should always render the cooldown input, whose visibility gate the category owns', async () => {
    wrapper = createWrapper();
    await flushPromises();

    const input = wrapper.find<HTMLInputElement>('[data-testid=auto-detect-tokens-cooldown-input] input');
    expect(input.exists()).toBe(true);
    expect(input.element.value).toBe('24');
  });

  it('should sync the local input value when the store setting changes externally', async () => {
    wrapper = createWrapper();
    await flushPromises();

    useSettingsRepo().updateFrontend({ autoDetectTokensCooldownHours: 48 });
    await flushPromises();
    await nextTick();

    const input = wrapper.find<HTMLInputElement>('[data-testid=auto-detect-tokens-cooldown-input] input');
    expect(input.element.value).toBe('48');
  });
});
