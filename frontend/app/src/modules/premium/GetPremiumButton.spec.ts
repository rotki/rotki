import { mount, type VueWrapper } from '@vue/test-utils';
import { set } from '@vueuse/shared';
import { createPinia, type Pinia, setActivePinia, storeToRefs } from 'pinia';
import { afterEach, beforeEach, describe, expect, it } from 'vitest';
import GetPremiumButton from '@/modules/premium/GetPremiumButton.vue';
import { usePremiumStore } from '@/modules/premium/use-premium-store';

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

  const createWrapper = (url?: string): VueWrapper<InstanceType<typeof GetPremiumButton>> =>
    mount(GetPremiumButton, {
      global: {
        plugins: [pinia],
      },
      props: { url },
    });

  it('should show get premium button for free users', () => {
    wrapper = createWrapper();

    const button = wrapper.find('[data-testid=get-premium-button]');
    expect(button.exists()).toBe(true);
    expect(button.text()).toContain('premium_settings.get');
  });

  it('should not render for premium users', () => {
    store = usePremiumStore();
    const { premium } = storeToRefs(store);
    set(premium, true);

    wrapper = createWrapper();

    const button = wrapper.find('[data-testid=get-premium-button]');
    expect(button.exists()).toBeFalsy();
  });

  it('should render a contextual upgrade link for premium users', () => {
    store = usePremiumStore();
    const { premium } = storeToRefs(store);
    set(premium, true);

    wrapper = createWrapper('https://rotki.com/products?utm_campaign=mcp_settings');

    expect(wrapper.find('[data-testid=get-premium-button]').exists()).toBe(true);
    expect(wrapper.find('a').attributes('href')).toContain('utm_campaign=mcp_settings');
  });
});
