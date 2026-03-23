import { mount, type VueWrapper } from '@vue/test-utils';
import { type Pinia, setActivePinia } from 'pinia';
import { afterEach, beforeEach, describe, expect, it } from 'vitest';
import GetPremiumButton from '@/components/premium/GetPremiumButton.vue';
import { usePremiumStore } from '@/store/session/premium';

describe('get-premium-button', () => {
  let wrapper: VueWrapper<InstanceType<typeof GetPremiumButton>>;
  let store: ReturnType<typeof usePremiumStore>;
  let pinia: Pinia;

  beforeEach((): void => {
    pinia = createPinia();
    setActivePinia(pinia);
  });

  afterEach((): void => {
    wrapper.unmount();
  });

  const createWrapper = (): VueWrapper<InstanceType<typeof GetPremiumButton>> =>
    mount(GetPremiumButton, {
      global: {
        plugins: [pinia],
      },
    });

  it('should show get premium button for free users', () => {
    wrapper = createWrapper();

    const button = wrapper.find('[data-cy=get-premium-button]');
    expect(button.exists()).toBe(true);
    expect(button.text()).toContain('premium_settings.get');
  });

  it('should not render for premium users', () => {
    store = usePremiumStore();
    const { premium } = storeToRefs(store);
    set(premium, true);

    wrapper = createWrapper();

    const button = wrapper.find('[data-cy=get-premium-button]');
    expect(button.exists()).toBeFalsy();
  });
});
