import type { SettingsUpdate } from '@/modules/settings/types/user-settings';
import { libraryDefaults } from '@test/utils/provide-defaults';
import { mount, type VueWrapper } from '@vue/test-utils';
import flushPromises from 'flush-promises';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import EvmChainsToIgnoreSettings from '@/components/settings/general/EvmChainsToIgnoreSettings.vue';
import { ApiValidationError } from '@/modules/api/types/errors';
import { useMainStore } from '@/store/main';

vi.mock('@/composables/api/settings/settings-api', async (): Promise<Record<string, unknown>> => {
  const mod = await vi.importActual<typeof import('@/composables/api/settings/settings-api')>(
    '@/composables/api/settings/settings-api',
  );
  return {
    ...mod,
    useSettingsApi: vi.fn().mockImplementation((): ReturnType<typeof mod.useSettingsApi> => {
      const mocked = mod.useSettingsApi();
      const setSettings = vi.fn().mockImplementation(async (params: SettingsUpdate): Promise<Awaited<ReturnType<typeof mocked.setSettings>>> => {
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

describe('evm-chains-to-ignore-settings', () => {
  let wrapper: VueWrapper<InstanceType<typeof EvmChainsToIgnoreSettings>>;

  function createWrapper(): VueWrapper<InstanceType<typeof EvmChainsToIgnoreSettings>> {
    const pinia = createPinia();
    setActivePinia(pinia);

    const mainStore = useMainStore();
    vi.spyOn(mainStore, 'setConnected').mockReturnValue(undefined);
    mainStore.connected = true;

    return mount(EvmChainsToIgnoreSettings, {
      pinia,
      provide: libraryDefaults,
    });
  }

  beforeEach(async (): Promise<void> => {
    wrapper = createWrapper();
    await flushPromises();
    vi.useFakeTimers();
  });

  it('should display no warning by default', () => {
    const input = wrapper.find('.input-value');
    expect(input.exists()).toBe(true);
    expect(input.text()).toBe('');
    expect(wrapper.find('.selections').exists()).toBe(true);
    expect(wrapper.find('.details').exists()).toBe(false);
  });

  it('should display success if correct chain values are passed', async () => {
    const chains = ['eth', 'avax', 'base', 'zksync_lite'];
    const input = wrapper.find('.input-value');
    const inputEl = wrapper.find<HTMLInputElement>('.input-value').element;
    await input.setValue(chains);

    await nextTick();
    await vi.advanceTimersByTimeAsync(2000);
    await flushPromises();

    expect(wrapper.find('.details').exists()).toBe(true);
    expect(wrapper.find('.details').text()).toContain('settings.saved');

    expect(inputEl.value).toMatch(chains.toString());
  });

  it('should display warning if wrong chain values are passed', async () => {
    const input = wrapper.find('.input-value');
    await input.setValue(['ethereum']);
    await nextTick();
    await vi.advanceTimersByTimeAsync(2000);
    await flushPromises();
    expect(wrapper.find('.details').text()).toContain('settings.not_saved');
  });
});
