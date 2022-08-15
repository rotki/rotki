import { mount, Wrapper } from '@vue/test-utils';
import { createPinia, PiniaVuePlugin, setActivePinia } from 'pinia';
import Vue from 'vue';
import Vuetify from 'vuetify';
import DefiWizard from '@/components/defi/wizard/DefiWizard.vue';
import { axiosSnakeCaseTransformer } from '@/services/axios-tranformers';
import { api } from '@/services/rotkehlchen-api';
import '../../../i18n';
import { FrontendSettings } from '@/types/frontend-settings';

vi.mock('@/services/rotkehlchen-api');

Vue.use(Vuetify);
Vue.use(PiniaVuePlugin);

describe('DefiWizard.vue', () => {
  let wrapper: Wrapper<any>;
  let settings: FrontendSettings;

  const createWrapper = () => {
    const vuetify = new Vuetify();
    const pinia = createPinia();
    setActivePinia(pinia);
    return mount(DefiWizard, {
      pinia,
      vuetify,
      stubs: ['v-tooltip', 'module-selector', 'module-address-selector', 'card']
    });
  };

  beforeEach(() => {
    settings = FrontendSettings.parse({});
    wrapper = createWrapper();
  });

  test('wizard completes when use default is pressed', async () => {
    expect.assertions(1);
    wrapper.find('.defi-wizard__use-default').trigger('click');
    await wrapper.vm.$nextTick();
    expect(api.setSettings).toBeCalledWith({
      frontendSettings: JSON.stringify(
        axiosSnakeCaseTransformer({ ...settings, defiSetupDone: true })
      )
    });
  });

  test('wizard completes when complete is pressed', async () => {
    expect.assertions(1);
    wrapper.find('.defi-wizard__select-modules').trigger('click');
    await wrapper.vm.$nextTick();
    wrapper.find('.defi-wizard__select-accounts').trigger('click');
    await wrapper.vm.$nextTick();
    wrapper.find('.defi-wizard__done').trigger('click');
    await wrapper.vm.$nextTick();
    expect(api.setSettings).toBeCalledWith({
      frontendSettings: JSON.stringify(
        axiosSnakeCaseTransformer({ ...settings, defiSetupDone: true })
      )
    });
  });
});
