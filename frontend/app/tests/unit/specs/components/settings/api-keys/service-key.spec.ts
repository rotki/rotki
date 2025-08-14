import { mount, type VueWrapper } from '@vue/test-utils';
import { createPinia, setActivePinia } from 'pinia';
import { afterEach, beforeEach, describe, expect, it } from 'vitest';
import ServiceKey from '@/components/settings/api-keys/ServiceKey.vue';

describe('serviceKey.vue', () => {
  let wrapper: VueWrapper<InstanceType<typeof ServiceKey>>;

  function createWrapper(): VueWrapper<InstanceType<typeof ServiceKey>> {
    const pinia = createPinia();
    setActivePinia(pinia);
    return mount(ServiceKey, {
      global: {
        plugins: [pinia],
      },
      props: {
        apiKey: '',
        name: 'etherscan',
      },
    });
  }

  beforeEach(() => {
    wrapper = createWrapper();
  });

  afterEach(() => {
    wrapper.unmount();
  });

  it('component leaves edit mode when updated with non-empty value', async () => {
    expect.assertions(2);
    await nextTick();
    expect(wrapper.find('[data-cy=service-key__api-key] input').attributes()).toMatchObject(
      expect.not.objectContaining({
        disabled: '',
      }),
    );
    await wrapper.setProps({
      apiKey: '1234',
    });
    await nextTick();
    expect(wrapper.find('[data-cy=service-key__api-key] input').attributes()).toMatchObject(
      expect.objectContaining({
        disabled: '',
      }),
    );
  });
});
