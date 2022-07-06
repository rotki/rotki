import { mount, Wrapper } from '@vue/test-utils';
import TabNavigation from '@/components/helper/TabNavigation.vue';
import { mountOptions } from '../../utils/mount';

describe('TabNavigation.vue', () => {
  let wrapper: Wrapper<any>;
  let nav: any;
  const data = [{ name: 'tab', routeTo: '/route/to/tab', hidden: true }];

  function createWrapper() {
    const options = mountOptions();
    return mount(TabNavigation, {
      ...options,
      propsData: {
        tabContents: data
      },
      mocks: { $route: { path: '/dashboard/info/' } }
    });
  }

  beforeAll(() => {
    wrapper = createWrapper();
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
