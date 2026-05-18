import { libraryDefaults } from '@test/utils/provide-defaults';
import { flushPromises, mount, type VueWrapper } from '@vue/test-utils';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import AutoDetectTokensCooldownSetting from '@/modules/settings/general/AutoDetectTokensCooldownSetting.vue';
import { useFrontendSettingsStore } from '@/modules/settings/use-frontend-settings-store';

const autoDetectTokensRef = ref<boolean>(true);

vi.mock('@/modules/settings/use-general-settings-store', () => ({
  useGeneralSettingsStore: (): { autoDetectTokens: typeof autoDetectTokensRef } => ({
    autoDetectTokens: autoDetectTokensRef,
  }),
}));

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

  beforeEach(() => {
    set(autoDetectTokensRef, true);
  });

  it('should render the cooldown input when auto-detect is enabled', async () => {
    wrapper = createWrapper();
    await flushPromises();

    const input = wrapper.find<HTMLInputElement>('[data-cy=auto-detect-tokens-cooldown-input] input');
    expect(input.exists()).toBe(true);
    expect(input.element.value).toBe('24');
  });

  it('should hide the cooldown input when auto-detect is disabled', async () => {
    set(autoDetectTokensRef, false);
    wrapper = createWrapper();
    await flushPromises();

    expect(wrapper.find('[data-cy=auto-detect-tokens-cooldown-input]').exists()).toBe(false);
  });

  it('should sync the local input value when the store setting changes externally', async () => {
    wrapper = createWrapper();
    await flushPromises();

    const store = useFrontendSettingsStore();
    store.update({ autoDetectTokensCooldownHours: 48 });
    await flushPromises();
    await nextTick();

    const input = wrapper.find<HTMLInputElement>('[data-cy=auto-detect-tokens-cooldown-input] input');
    expect(input.element.value).toBe('48');
  });
});
