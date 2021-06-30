import { mount, Wrapper } from '@vue/test-utils';
import Vue from 'vue';
import Vuetify from 'vuetify';
import DefiWizard from '@/components/defi/wizard/DefiWizard.vue';
import { DEFI_SETUP_DONE } from '@/store/settings/consts';
import store from '@/store/store';
import '../../../i18n';

Vue.use(Vuetify);

describe('DefiWizard.vue', () => {
  let wrapper: Wrapper<DefiWizard>;
  function createWrapper() {
    const vuetify = new Vuetify();
    return mount(DefiWizard, {
      store,
      vuetify,
      stubs: ['v-tooltip', 'module-selector', 'module-address-selector', 'card']
    });
  }

  beforeEach(() => {
    wrapper = createWrapper();
  });

  test('wizard completes when use default is pressed', async () => {
    expect.assertions(1);
    wrapper.find('.defi-wizard__use-default').trigger('click');
    await wrapper.vm.$nextTick();
    // @ts-ignore
    expect(store.state.settings[DEFI_SETUP_DONE]).toBeTruthy();
  });

  test('wizard completes when complete is pressed', async () => {
    expect.assertions(1);
    wrapper.find('.defi-wizard__select-modules').trigger('click');
    await wrapper.vm.$nextTick();
    wrapper.find('.defi-wizard__select-accounts').trigger('click');
    await wrapper.vm.$nextTick();
    wrapper.find('.defi-wizard__done').trigger('click');
    await wrapper.vm.$nextTick();
    // @ts-ignore
    expect(store.state.settings[DEFI_SETUP_DONE]).toBeTruthy();
  });
});
