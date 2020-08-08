import { mount, Wrapper } from '@vue/test-utils';
import flushPromises from 'flush-promises/index';
import Vue from 'vue';
import Vuetify from 'vuetify';
import PremiumSettings from '@/components/settings/PremiumSettings.vue';
import { interop } from '@/electron-interop';
import { Api } from '@/plugins/api';
import { Interop } from '@/plugins/interop';
import { api } from '@/services/rotkehlchen-api';
import store from '@/store/store';

jest.mock('@/electron-interop');
jest.mock('@/services/rotkehlchen-api');

Vue.use(Vuetify);
Vue.use(Api);
Vue.use(Interop);

describe('PremiumSettings.vue', () => {
  let wrapper: Wrapper<PremiumSettings>;

  function createWrapper() {
    const vuetify = new Vuetify();
    return mount(PremiumSettings, {
      store,
      vuetify,
      stubs: ['v-tooltip', 'v-dialog']
    });
  }

  beforeEach(() => {
    wrapper = createWrapper();
  });

  test('updates premium status upon setting keys', async () => {
    api.setPremiumCredentials = jest.fn().mockResolvedValue({ result: true });
    const apiKey = wrapper.find('.premium-settings__fields__api-key input');
    const apiSecret = wrapper.find(
      '.premium-settings__fields__api-secret input'
    );

    (apiKey.element as HTMLInputElement).value = '1234';
    (apiSecret.element as HTMLInputElement).value = '1234';

    apiKey.trigger('input');
    apiSecret.trigger('input');
    await wrapper.vm.$nextTick();
    wrapper.find('.premium-settings__button__setup').trigger('click');
    await wrapper.vm.$nextTick();
    await flushPromises();

    expect(interop.premiumUserLoggedIn).toHaveBeenCalledWith(true);
  });

  test('updates premium status upon removing keys', async () => {
    store.commit('session/premium', true);
    await wrapper.vm.$nextTick();
    api.deletePremiumCredentials = jest
      .fn()
      .mockResolvedValue({ result: true });

    wrapper.find('.premium-settings__button__delete').trigger('click');
    await wrapper.vm.$nextTick();
    wrapper.find('.confirm-dialog__buttons__confirm').trigger('click');
    await wrapper.vm.$nextTick();
    await flushPromises();

    expect(interop.premiumUserLoggedIn).toHaveBeenCalledWith(false);
  });
});
