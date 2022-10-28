import { mount, ThisTypedMountOptions, Wrapper } from '@vue/test-utils';
import { createPinia, PiniaVuePlugin, setActivePinia } from 'pinia';
import Vue from 'vue';
import Vuetify from 'vuetify';
import TabNavigation from '@/components/helper/TabNavigation.vue';
import { getClass } from '@/types/tabs';

Vue.use(Vuetify);
Vue.use(PiniaVuePlugin);

describe('TabNavigation.vue', () => {
  let wrapper: Wrapper<any>;
  let nav: any;
  const data = [{ name: 'tab', routeTo: '/route/to/tab', hidden: true }];

  function createWrapper(options: ThisTypedMountOptions<any> = {}) {
    const vuetify = new Vuetify();
    const pinia = createPinia();
    setActivePinia(pinia);
    return mount(TabNavigation, {
      pinia,
      vuetify,
      ...options
    });
  }

  beforeAll(() => {
    wrapper = createWrapper({
      propsData: {
        tabContents: data
      },
      mocks: { $route: { path: '/dashboard/info/' } }
    });
    nav = wrapper.vm as any;
  });

  test('gets proper class out of path', async () => {
    const className = getClass('/dashboard/info');
    expect(className).toEqual('dashboard__info');
  });

  test('do not return any tabs that are hidden', async () => {
    expect(wrapper.findAll('.tab-navigation__tabs__tab')).toHaveLength(0);
  });
});
