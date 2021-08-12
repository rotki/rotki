import VueCompositionAPI from '@vue/composition-api';
import { mount, ThisTypedMountOptions, Wrapper } from '@vue/test-utils';
import Vue from 'vue';
import Vuetify from 'vuetify';
import Vuex from 'vuex';
import TabNavigation from '@/components/helper/TabNavigation.vue';
import store from '@/store/store';

Vue.use(Vuetify);
Vue.use(Vuex);
Vue.use(VueCompositionAPI);

describe('TabNavigation.vue', () => {
  let wrapper: Wrapper<any>;
  let nav: any;
  const data = [{ name: 'tab', routeTo: '/route/to/tab', hidden: true }];

  function createWrapper(options: ThisTypedMountOptions<any> = {}) {
    const vuetify = new Vuetify();
    return mount(TabNavigation, {
      store,
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
    const className = nav.getClass('/dashboard/info');
    expect(className).toEqual('dashboard__info');
  });

  test('do not return any tabs that are hidden', async () => {
    expect(nav.visibleTabs).toMatchObject([]);
  });
});
