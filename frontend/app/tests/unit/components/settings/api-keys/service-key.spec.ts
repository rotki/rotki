import { mount, Wrapper } from '@vue/test-utils';
import { createPinia, setActivePinia } from 'pinia';
import Vuetify from 'vuetify';
import ServiceKey from '@/components/settings/api-keys/ServiceKey.vue';

describe('ServiceKey.vue', () => {
  let wrapper: Wrapper<any>;

  function createWrapper(): Wrapper<any> {
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
    await wrapper.setProps({
      value: '1234'
    });
    await wrapper.vm.$nextTick();
    expect(
      wrapper.find('.service-key__api-key input').attributes('disabled')
    ).toBe('disabled');
  });
});
