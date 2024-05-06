import { type Wrapper, mount } from '@vue/test-utils';
import { promiseTimeout } from '@vueuse/core';
import flushPromises from 'flush-promises';
import Vuetify from 'vuetify';
import { ApiValidationError } from '@/types/api/errors';
import EvmChainsToIgnoreSettings from '@/components/settings/general/EvmChainsToIgnoreSettings.vue';
import { libraryDefaults } from '../../../utils/provide-defaults';
import type { SettingsUpdate } from '@/types/user';

vi.mock('@/store/main', () => ({
  useMainStore: vi.fn().mockReturnValue({
    connected: true,
    setConnected: vi.fn(),
    connect: vi.fn(),
  }),
}));

vi.mock('@/composables/api/settings/settings-api', async () => {
  const mod = await vi.importActual<typeof import('@/composables/api/settings/settings-api')>(
    '@/composables/api/settings/settings-api',
  );
  return {
    ...mod,
    useSettingsApi: vi.fn().mockImplementation(() => {
      const mocked = mod.useSettingsApi();
      const setSettings = vi.fn().mockImplementation((params: SettingsUpdate) => {
        if (params.evmchainsToSkipDetection?.includes('ethereum'))
          throw new ApiValidationError('{"settings": {"evmchains_to_skip_detection": {"1": ["Failed to deserialize SupportedBlockchain value ethereum"]}}}');

        return mocked.setSettings(params);
      });

      return {
        ...mocked,
        setSettings,
      };
    }),
  };
});

describe('evmChainsToIgnoreSettings.vue', () => {
  let wrapper: Wrapper<any>;

  function createWrapper() {
    const vuetify = new Vuetify();
    const pinia = createPinia();
    setActivePinia(pinia);
    return mount(EvmChainsToIgnoreSettings, {
      pinia,
      vuetify,
      provide: libraryDefaults,
    });
  }

  beforeEach(async () => {
    wrapper = createWrapper();
    await flushPromises();
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
    await input.trigger('input', { value: chains });

    await nextTick();
    await promiseTimeout(2000);
    await flushPromises();

    expect(wrapper.find('.details').exists()).toBeTruthy();
    expect(wrapper.find('.details').text()).toContain('settings.saved');

    expect(inputEl.value).toMatchObject(chains.toString());
  });

  it('displays warning if wrong chain values are passed', async () => {
    const input = wrapper.find('.input-value');

    await input.trigger('input', { value: ['ethereum'] });
    await nextTick();
    await promiseTimeout(2000);
    await flushPromises();

    expect(wrapper.find('.details').text()).toContain('settings.not_saved');
  });
});
