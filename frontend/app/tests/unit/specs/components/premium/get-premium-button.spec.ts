import { type Wrapper, mount } from '@vue/test-utils';
import Vuetify from 'vuetify';
import { type Pinia, setActivePinia } from 'pinia';
import GetPremiumButton from '@/components/premium/GetPremiumButton.vue';

describe('GetPremiumButton.vue', () => {
  let wrapper: Wrapper<GetPremiumButton>;
  let store: ReturnType<typeof usePremiumStore>;
  let pinia: Pinia;

  beforeEach(() => {
    pinia = createPinia();
    setActivePinia(pinia);
  });

  const createWrapper = () => {
    const vuetify = new Vuetify();
    return mount(GetPremiumButton, {
      pinia,
      vuetify
    });
  };

  test('should show get premium button', () => {
    wrapper = createWrapper();

    expect(wrapper.find('[data-cy=get-premium-button]').exists()).toBeTruthy();
  });

  test('should not show get premium button', () => {
    store = usePremiumStore();
    const { premium } = storeToRefs(store);
    set(premium, true);

    wrapper = createWrapper();

    expect(wrapper.find('[data-cy=get-premium-button]').exists()).toBeFalsy();
  });
});
