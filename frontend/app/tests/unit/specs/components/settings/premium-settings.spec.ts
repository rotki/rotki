import { mount, type VueWrapper } from '@vue/test-utils';
import flushPromises from 'flush-promises/index';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { usePremiumCredentialsApi } from '@/composables/api/session/premium-credentials';
import { useInterop } from '@/composables/electron-interop';
import { usePremium } from '@/composables/premium';
import PremiumSettings from '@/pages/api-keys/premium/index.vue';
import { useConfirmStore } from '@/store/confirm';

vi.mock('@/composables/electron-interop', () => {
  const mockInterop = {
    premiumUserLoggedIn: vi.fn(),
  };
  return {
    useInterop: vi.fn().mockReturnValue(mockInterop),
    interop: mockInterop,
  };
});

vi.mock('@/composables/api/session/premium-credentials', () => ({
  usePremiumCredentialsApi: vi.fn().mockReturnValue({}),
}));

describe('premiumSettings.vue', () => {
  let wrapper: VueWrapper<InstanceType<typeof PremiumSettings>>;
  let api: ReturnType<typeof usePremiumCredentialsApi>;

  function createWrapper() {
    const pinia = createPinia();
    setActivePinia(pinia);
    return mount(PremiumSettings, {
      global: {
        plugins: [pinia],
        stubs: ['i18n-t', 'card-title'],
      },
    });
  }

  beforeEach(() => {
    document.body.dataset.app = 'true';
    wrapper = createWrapper();
    api = usePremiumCredentialsApi();
  });

  afterEach(() => {
    wrapper.unmount();
  });

  it('updates premium status upon setting keys', async () => {
    api.setPremiumCredentials = vi.fn().mockResolvedValue({ result: true });
    const apiKey = wrapper.find('[data-cy=premium__api-key] input');
    const apiSecret = wrapper.find('[data-cy=premium__api-secret] input');

    await apiKey.setValue('1234');
    await apiSecret.setValue('1234');

    await nextTick();
    await wrapper.find('[data-cy=premium__setup]').trigger('click');
    await nextTick();
    await flushPromises();

    const { premiumUserLoggedIn } = useInterop();
    expect(premiumUserLoggedIn).toHaveBeenCalledWith(true);
  });

  it('updates premium status upon removing keys', async () => {
    const premium = usePremium();
    set(premium, true);

    await nextTick();
    api.deletePremiumCredentials = vi.fn().mockResolvedValue({ result: true });

    await wrapper.find('[data-cy=premium__delete]').trigger('click');
    await nextTick();
    await flushPromises();

    const { confirm } = useConfirmStore();
    await confirm();
    await flushPromises();

    const { premiumUserLoggedIn } = useInterop();
    expect(premiumUserLoggedIn).toHaveBeenCalledWith(false);
  });
});
