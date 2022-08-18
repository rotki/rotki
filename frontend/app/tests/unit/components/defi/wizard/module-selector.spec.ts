import { mount, Wrapper } from '@vue/test-utils';
import { set } from '@vueuse/core';
import {
  createPinia,
  Pinia,
  PiniaVuePlugin,
  setActivePinia,
  storeToRefs
} from 'pinia';
import Vue from 'vue';
import Vuetify from 'vuetify';
import ModuleSelector from '@/components/defi/wizard/ModuleSelector.vue';
import { api } from '@/services/rotkehlchen-api';
import { useGeneralSettingsStore } from '@/store/settings/general';
import { Module } from '@/types/modules';
import '../../../i18n';

vi.mock('@/services/rotkehlchen-api');

Vue.use(Vuetify);
Vue.use(PiniaVuePlugin);

describe('ModuleSelector.vue', () => {
  let wrapper: Wrapper<ModuleSelector>;
  let settingsStore: ReturnType<typeof useGeneralSettingsStore>;
  let pinia: Pinia;

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

    document.body.setAttribute('data-app', 'true');
    const { activeModules } = storeToRefs(settingsStore);
    set(activeModules, [Module.AAVE]);
    wrapper = createWrapper();
  });

  test('displays active modules', async () => {
    expect(wrapper.find('#defi-module-aave').exists()).toBe(true);
  });

  test('removes active modules on click', async () => {
    expect.assertions(2);
    api.setSettings = vi.fn().mockResolvedValue({ active_modules: [] });
    wrapper.find('#defi-module-aave').find('button').trigger('click');
    await wrapper.vm.$nextTick();
    expect(wrapper.find('#defi-module-aave').exists()).toBe(false);
    expect(settingsStore.activeModules).toEqual([]);
  });
});
