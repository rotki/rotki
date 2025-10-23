import type { SettingsUpdate } from '@/types/user';
import { libraryDefaults } from '@test/utils/provide-defaults';
import { mount, type VueWrapper } from '@vue/test-utils';
import flushPromises from 'flush-promises';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import EvmChainsToIgnoreSettings from '@/components/settings/general/EvmChainsToIgnoreSettings.vue';
import { useMainStore } from '@/store/main';
import { ApiValidationError } from '@/types/api/errors';

vi.mock('@/composables/api/settings/settings-api', async () => {
  const mod = await vi.importActual<typeof import('@/composables/api/settings/settings-api')>(
    '@/composables/api/settings/settings-api',
  );
  return {
    ...mod,
    useSettingsApi: vi.fn().mockImplementation(() => {
      const mocked = mod.useSettingsApi();
      const setSettings = vi.fn().mockImplementation(async (params: SettingsUpdate) => {
        if (params.evmchainsToSkipDetection?.includes('ethereum')) {
          throw new ApiValidationError(
            '{"settings": {"evmchains_to_skip_detection": {"1": ["Failed to deserialize SupportedBlockchain value ethereum"]}}}',
          );
        }

        return mocked.setSettings(params);
      });

      return {
        ...mocked,
        setSettings,
      };
    }),
  };
});

describe('settings/EvmChainsToIgnoreSettings.vue', () => {
  let wrapper: VueWrapper<InstanceType<typeof EvmChainsToIgnoreSettings>>;

  function createWrapper() {
    const pinia = createPinia();
    setActivePinia(pinia);

    const mainStore = useMainStore();
    vi.spyOn(mainStore, 'setConnected').mockReturnValue(undefined);
    vi.spyOn(mainStore, 'connect').mockReturnValue(undefined);
    mainStore.connected = true;

    return mount(EvmChainsToIgnoreSettings, {
      pinia,
      provide: libraryDefaults,
    });
  }

  beforeEach(async () => {
    wrapper = createWrapper();
    await flushPromises();
    vi.useFakeTimers();
  });

  it('displays no warning by default', () => {
    const input = wrapper.find('.input-value');
    expect(input.exists()).toBeTruthy();
    expect(input.text()).toBe('');
    expect(wrapper.find('.selections').exists()).toBeTruthy();
    expect(wrapper.find('.details').exists()).toBeFalsy();
  });

  it('displays success if correct chain values are passed', async () => {
    const chains = ['eth', 'avax', 'base', 'zksync_lite'];
    const input = wrapper.find('.input-value');
    const inputEl = input.element as HTMLInputElement;
    await input.setValue(chains);

    await nextTick();
    await vi.advanceTimersByTimeAsync(2000);
    await flushPromises();

    expect(wrapper.find('.details').exists()).toBeTruthy();
    expect(wrapper.find('.details').text()).toContain('settings.saved');

    expect(inputEl.value).toMatch(chains.toString());
  });

  it('displays warning if wrong chain values are passed', async () => {
    const input = wrapper.find('.input-value');
    await input.setValue(['ethereum']);
    await nextTick();
    await vi.advanceTimersByTimeAsync(2000);
    await flushPromises();
    expect(wrapper.find('.details').text()).toContain('settings.not_saved');
  });
});
