import {
  type ThisTypedMountOptions,
  type Wrapper,
  mount
} from '@vue/test-utils';
import { createPinia, setActivePinia } from 'pinia';
import Vuetify from 'vuetify';
import TabNavigation from '@/components/helper/TabNavigation.vue';
import { getClass } from '@/types/tabs';

vi.mock('vue-router/composables', () => ({
  useRoute: vi.fn().mockReturnValue({
    path: '/dashboard/info/'
  })
}));

describe('TabNavigation.vue', () => {
  let wrapper: Wrapper<any>;
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
      }
    });
  });

  test('gets proper class out of path', async () => {
    const className = getClass('/dashboard/info');
    expect(className).toEqual('dashboard__info');
  });

  test('do not return any tabs that are hidden', async () => {
    expect(wrapper.findAll('.tab-navigation__tabs__tab')).toHaveLength(0);
  });
});
