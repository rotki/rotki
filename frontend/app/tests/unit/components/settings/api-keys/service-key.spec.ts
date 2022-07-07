import { mount, Wrapper } from '@vue/test-utils';
import ServiceKey from '@/components/settings/api-keys/ServiceKey.vue';
import { mountOptions } from '../../../utils/mount';

describe('ServiceKey.vue', () => {
  let wrapper: Wrapper<ServiceKey>;

  function createWrapper(): Wrapper<ServiceKey> {
    const options = mountOptions();
    return mount(ServiceKey, {
      ...options,
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
