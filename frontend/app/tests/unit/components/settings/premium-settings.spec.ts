import { mount, Wrapper } from '@vue/test-utils';
import { set } from '@vueuse/core';
import flushPromises from 'flush-promises/index';
import {
  createPinia,
  PiniaVuePlugin,
  setActivePinia,
  storeToRefs
} from 'pinia';
import Vue from 'vue';
import Vuetify from 'vuetify';
import Card from '@/components/helper/Card.vue';
import PremiumSettings from '@/components/settings/PremiumSettings.vue';
import { interop } from '@/electron-interop';
import { Api } from '@/plugins/api';
import { Interop } from '@/plugins/interop';
import { api } from '@/services/rotkehlchen-api';
import { usePremiumStore } from '@/store/session/premium';
import '../../i18n';

vi.mock('@/electron-interop', () => {
  const mockInterop = {
    premiumUserLoggedIn: vi.fn()
  };
  return {
    useInterop: vi.fn().mockReturnValue(mockInterop),
    interop: mockInterop
  };
});
vi.mock('@/services/rotkehlchen-api');

Vue.use(Vuetify);
Vue.use(Api);
Vue.use(Interop);
Vue.use(PiniaVuePlugin);

describe('PremiumSettings.vue', () => {
  let wrapper: Wrapper<PremiumSettings>;

  function createWrapper() {
    const vuetify = new Vuetify();
    const pinia = createPinia();
    setActivePinia(pinia);
    return mount(PremiumSettings, {
      pinia,
      vuetify,
      components: {
        Card
      },
      stubs: ['v-tooltip', 'v-dialog', 'i18n', 'card-title']
    });
  }

  beforeEach(() => {
    wrapper = createWrapper();
  });

  test('updates premium status upon setting keys', async () => {
    api.setPremiumCredentials = vi.fn().mockResolvedValue({ result: true });
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
    const { premium } = storeToRefs(usePremiumStore());
    set(premium, true);

    await wrapper.vm.$nextTick();
    api.deletePremiumCredentials = vi.fn().mockResolvedValue({ result: true });

    await (wrapper.vm as any).remove();
    await wrapper.vm.$nextTick();
    await flushPromises();

    expect(interop.premiumUserLoggedIn).toHaveBeenCalledWith(false);
  });
});
