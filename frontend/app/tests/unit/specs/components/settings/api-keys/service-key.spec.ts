import { type VueWrapper, mount } from '@vue/test-utils';
import { createPinia, setActivePinia } from 'pinia';
import { createVuetify } from 'vuetify';
import ServiceKey from '@/components/settings/api-keys/ServiceKey.vue';

describe('serviceKey.vue', () => {
  let wrapper: VueWrapper<InstanceType<typeof ServiceKey>>;

  function createWrapper(): VueWrapper<InstanceType<typeof ServiceKey>> {
    const vuetify = createVuetify();
    const pinia = createPinia();
    setActivePinia(pinia);
    return mount(ServiceKey, {
      global: {
        plugins: [
          pinia,
          vuetify,
        ],
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

  it('component leaves edit mode when updated with non-empty value', async () => {
    expect.assertions(2);
    await nextTick();

    expect(
      wrapper.find('[data-cy=service-key__api-key] input').attributes(),
    ).toMatchObject(expect.not.objectContaining({
      disabled: '',
    }));
    await wrapper.setProps({
      apiKey: '1234',
    });
    await nextTick();
    expect(
      wrapper.find('[data-cy=service-key__api-key] input').attributes(),
    ).toMatchObject(expect.objectContaining({
      disabled: '',
    }));
  });
});
