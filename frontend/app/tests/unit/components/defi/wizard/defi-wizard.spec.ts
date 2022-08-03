import { createTestingPinia } from '@pinia/testing';
import { mount, Wrapper } from '@vue/test-utils';
import { PiniaVuePlugin } from 'pinia';
import Vue from 'vue';
import Vuetify from 'vuetify';
import DefiWizard from '@/components/defi/wizard/DefiWizard.vue';
import { useFrontendSettingsStore } from '@/store/settings';
import store from '@/store/store';
import '../../../i18n';

Vue.use(Vuetify);
Vue.use(PiniaVuePlugin);

describe('DefiWizard.vue', () => {
  let wrapper: Wrapper<any>;
  function createWrapper() {
    const vuetify = new Vuetify();
    return mount(DefiWizard, {
      store,
      pinia: createTestingPinia(),
      vuetify,
      stubs: ['v-tooltip', 'module-selector', 'module-address-selector', 'card']
    });
  }

  beforeEach(() => {
    wrapper = createWrapper();
  });

  test('wizard completes when use default is pressed', async () => {
    const store = useFrontendSettingsStore();
    expect.assertions(1);
    wrapper.find('.defi-wizard__use-default').trigger('click');
    await wrapper.vm.$nextTick();
    expect(store.updateSetting).toBeCalledWith({ defiSetupDone: true });
  });

  test('wizard completes when complete is pressed', async () => {
    const store = useFrontendSettingsStore();
    expect.assertions(1);
    wrapper.find('.defi-wizard__select-modules').trigger('click');
    await wrapper.vm.$nextTick();
    wrapper.find('.defi-wizard__select-accounts').trigger('click');
    await wrapper.vm.$nextTick();
    wrapper.find('.defi-wizard__done').trigger('click');
    await wrapper.vm.$nextTick();
    expect(store.updateSetting).toBeCalledWith({ defiSetupDone: true });
  });
});
