import { mount, type VueWrapper } from '@vue/test-utils';
import { type Pinia, setActivePinia } from 'pinia';
import { afterEach, beforeEach, describe, expect, it } from 'vitest';
import GetPremiumButton from '@/components/premium/GetPremiumButton.vue';
import { usePremiumStore } from '@/store/session/premium';

describe('getPremiumButton.vue', () => {
  let wrapper: VueWrapper<InstanceType<typeof GetPremiumButton>>;
  let store: ReturnType<typeof usePremiumStore>;
  let pinia: Pinia;

  beforeEach(() => {
    pinia = createPinia();
    setActivePinia(pinia);
  });

  afterEach(() => {
    wrapper.unmount();
  });

  const createWrapper = () =>
    mount(GetPremiumButton, {
      global: {
        plugins: [pinia],
      },
    });

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
