import { mount, Wrapper } from '@vue/test-utils';
import { createPinia, PiniaVuePlugin, setActivePinia } from 'pinia';
import Vue from 'vue';
import Vuetify from 'vuetify';
import ServiceKey from '@/components/settings/api-keys/ServiceKey.vue';
import '../../../i18n';

Vue.use(Vuetify);
Vue.use(PiniaVuePlugin);

describe('ServiceKey.vue', () => {
  let wrapper: Wrapper<ServiceKey>;

  function createWrapper(): Wrapper<ServiceKey> {
    const vuetify = new Vuetify();
    const pinia = createPinia();
    setActivePinia(pinia);
    return mount(ServiceKey, {
      pinia,
      vuetify,
      propsData: {
        value: '',
        title: 'test'
      }
    });
  }

  beforeEach(() => {
    wrapper = createWrapper();
  });

  test('component leaves edit mode when updated with non-empty value', async () => {
    expect.assertions(2);
    await wrapper.vm.$nextTick();
    expect(
      wrapper.find('.service-key__api-key input').attributes('disabled')
    ).toBeUndefined();
    wrapper.setProps({
      value: '1234'
    });
    await wrapper.vm.$nextTick();
    expect(
      wrapper.find('.service-key__api-key input').attributes('disabled')
    ).toBe('disabled');
  });
});
