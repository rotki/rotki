import { mount, Wrapper } from '@vue/test-utils';
import Vue from 'vue';
import Vuetify from 'vuetify';
import ModuleSelector from '@/components/defi/wizard/ModuleSelector.vue';
import { api } from '@/services/rotkehlchen-api';
import store from '@/store/store';
import '../../../i18n';
import { Module } from '@/types/modules';
import { GeneralSettings } from '@/types/user';

jest.mock('@/services/rotkehlchen-api');

Vue.use(Vuetify);

describe('ModuleSelector.vue', () => {
  let wrapper: Wrapper<ModuleSelector>;

  function createWrapper() {
    const vuetify = new Vuetify();
    return mount(ModuleSelector, {
      store,
      vuetify,
      stubs: ['v-tooltip']
    });
  }

  beforeEach(() => {
    document.body.setAttribute('data-app', 'true');
    const settings: GeneralSettings = {
      ...store.state.session!.generalSettings,
      activeModules: [Module.AAVE]
    };
    store.commit('session/generalSettings', settings);

    wrapper = createWrapper();
  });

  test('displays active modules', async () => {
    expect(wrapper.find('#defi-module-aave').exists()).toBe(true);
  });

  test('removes active modules on click', async () => {
    expect.assertions(2);
    api.setSettings = jest.fn().mockResolvedValue({ active_modules: [] });
    wrapper.find('#defi-module-aave').find('button').trigger('click');
    await wrapper.vm.$nextTick();
    expect(wrapper.find('#defi-module-aave').exists()).toBe(false);
    expect(store.state.session!.generalSettings.activeModules).toEqual([]);
  });
});
