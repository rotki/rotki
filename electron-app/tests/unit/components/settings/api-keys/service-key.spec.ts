import { mount, Wrapper } from '@vue/test-utils';
import Vue from 'vue';
import Vuetify from 'vuetify';
import ServiceKey from '@/components/settings/api-keys/ServiceKey.vue';
import store from '@/store/store';

Vue.use(Vuetify);

describe('ServiceKey.vue', () => {
  let vuetify: typeof Vuetify;
  let wrapper: Wrapper<ServiceKey>;

  function createWrapper(): Wrapper<ServiceKey> {
    vuetify = new Vuetify();
    return mount(ServiceKey, {
      store,
      vuetify,
      attachToDocument: true,
      propsData: {
        value: '',
        title: 'test'
      }
    });
  }

  beforeEach(() => {
    wrapper = createWrapper();
    vuetify = new Vuetify();
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
