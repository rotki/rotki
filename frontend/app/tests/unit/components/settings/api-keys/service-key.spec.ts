import { mount, Wrapper } from '@vue/test-utils';
import { createPinia, PiniaVuePlugin, setActivePinia } from 'pinia';
import Vue from 'vue';
import Vuetify from 'vuetify';
import ServiceKey from '@/components/settings/api-keys/ServiceKey.vue';
import { mockT, mockTc } from '../../../i18n';

Vue.use(Vuetify);
Vue.use(PiniaVuePlugin);

vi.mock('vue-i18n-composable', async () => {
  const mod = await vi.importActual<typeof import('vue-i18n-composable')>(
    'vue-i18n-composable'
  );

  return {
    ...mod,
    useI18n: () => ({
      t: mockT,
      tc: mockTc
    })
  };
});

vi.mock('vue', async () => {
  const mod = await vi.importActual<typeof import('vue')>('vue');
  return {
    ...mod,
    useListeners: vi.fn(),
    useAttrs: vi.fn()
  };
});

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
