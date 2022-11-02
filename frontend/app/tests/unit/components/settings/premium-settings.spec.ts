import { mount, Wrapper } from '@vue/test-utils';
import { set } from '@vueuse/core';
import flushPromises from 'flush-promises/index';
import { createPinia, setActivePinia, storeToRefs } from 'pinia';
import Vuetify from 'vuetify';
import Card from '@/components/helper/Card.vue';
import { interop } from '@/electron-interop';
import PremiumSettings from '@/pages/settings/api-keys/premium/index.vue';
import { api } from '@/services/rotkehlchen-api';
import { usePremiumStore } from '@/store/session/premium';

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
    document.body.setAttribute('data-app', 'true');
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

    await apiKey.trigger('input');
    await apiSecret.trigger('input');
    await wrapper.vm.$nextTick();
    await wrapper.find('.premium-settings__button__setup').trigger('click');
    await wrapper.vm.$nextTick();
    await flushPromises();

    expect(interop.premiumUserLoggedIn).toHaveBeenCalledWith(true);
  });

  test('updates premium status upon removing keys', async () => {
    const { premium } = storeToRefs(usePremiumStore());
    set(premium, true);

    await wrapper.vm.$nextTick();
    api.deletePremiumCredentials = vi.fn().mockResolvedValue({ result: true });

    await wrapper.find('.premium-settings__button__delete').trigger('click');
    await wrapper.vm.$nextTick();
    await flushPromises();
    await wrapper.find('[data-cy=button-confirm]').trigger('click');
    await wrapper.vm.$nextTick();
    await flushPromises();

    expect(interop.premiumUserLoggedIn).toHaveBeenCalledWith(false);
  });
});
