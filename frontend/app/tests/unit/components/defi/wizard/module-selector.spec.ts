import { mount, Wrapper } from '@vue/test-utils';
import { createPinia, Pinia, setActivePinia } from 'pinia';
import Vuetify from 'vuetify';
import ModuleSelector from '@/components/defi/wizard/ModuleSelector.vue';
import { defaultGeneralSettings } from '@/data/factories';
import { useSettingsApi } from '@/services/settings/settings-api';
import { useGeneralSettingsStore } from '@/store/settings/general';
import { useCurrencies } from '@/types/currencies';
import { Module } from '@/types/modules';

vi.mock('@/services/settings/settings-api', () => ({
  useSettingsApi: vi.fn().mockReturnValue({
    setSettings: vi.fn()
  })
}));

describe('ModuleSelector.vue', () => {
  let wrapper: Wrapper<ModuleSelector>;
  let settingsStore: ReturnType<typeof useGeneralSettingsStore>;
  let pinia: Pinia;
  let api: ReturnType<typeof useSettingsApi>;

  const createWrapper = () => {
    const vuetify = new Vuetify();
    return mount(ModuleSelector, {
      pinia,
      vuetify,
      stubs: ['v-tooltip', 'card']
    });
  };

  beforeEach(() => {
    pinia = createPinia();
    setActivePinia(pinia);
    settingsStore = useGeneralSettingsStore(pinia);
    api = useSettingsApi();
    const { defaultCurrency } = useCurrencies();

    document.body.setAttribute('data-app', 'true');
    settingsStore.update({
      ...defaultGeneralSettings(get(defaultCurrency)),
      activeModules: [Module.AAVE]
    });
    wrapper = createWrapper();
    api.setSettings = vi.fn();
  });

  test('displays active modules', async () => {
    expect(wrapper.find('#defi-module-aave').exists()).toBe(true);
  });

  test('removes active modules on click', async () => {
    expect.assertions(2);
    api.setSettings = vi.fn().mockResolvedValue({ active_modules: [] });
    await wrapper.find('#defi-module-aave').find('button').trigger('click');
    await wrapper.vm.$nextTick();
    expect(wrapper.find('#defi-module-aave').exists()).toBe(false);
    expect(settingsStore.activeModules).toEqual([]);
  });
});
