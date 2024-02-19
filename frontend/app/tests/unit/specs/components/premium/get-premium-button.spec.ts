import { type VueWrapper, mount } from '@vue/test-utils';
import { createVuetify } from 'vuetify';
import { type Pinia, setActivePinia } from 'pinia';
import GetPremiumButton from '@/components/premium/GetPremiumButton.vue';

describe('getPremiumButton.vue', () => {
  let wrapper: VueWrapper<InstanceType<typeof GetPremiumButton>>;
  let store: ReturnType<typeof usePremiumStore>;
  let pinia: Pinia;

  beforeEach(() => {
    pinia = createPinia();
    setActivePinia(pinia);
  });

  const createWrapper = () => {
    const vuetify = createVuetify();
    return mount(GetPremiumButton, {
      global: {
        plugins: [pinia, vuetify],
      },
    });
  };

  it('should show get premium button', () => {
    wrapper = createWrapper();

    expect(wrapper.find('[data-cy=get-premium-button]').exists()).toBeTruthy();
  });

  it('should not show get premium button', () => {
    store = usePremiumStore();
    const { premium } = storeToRefs(store);
    set(premium, true);

    wrapper = createWrapper();

    expect(wrapper.find('[data-cy=get-premium-button]').exists()).toBeFalsy();
  });
});
