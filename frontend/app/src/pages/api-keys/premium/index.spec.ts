import { libraryDefaults } from '@test/utils/provide-defaults';
import { mount, type VueWrapper } from '@vue/test-utils';
import flushPromises from 'flush-promises/index';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { useConfirmStore } from '@/modules/core/common/use-confirm-store';
import { usePremium } from '@/modules/premium/use-premium';
import { usePremiumCredentialsApi } from '@/modules/premium/use-premium-credentials-api';
import { useInterop } from '@/modules/shell/app/use-electron-interop';
import PremiumSettings from '@/pages/api-keys/premium/index.vue';

vi.mock('@/modules/shell/app/use-electron-interop', (): Record<string, unknown> => {
  const mockInterop = {
    premiumUserLoggedIn: vi.fn(),
  };
  return {
    useInterop: vi.fn().mockReturnValue(mockInterop),
    interop: mockInterop,
  };
});

vi.mock('@/modules/premium/use-premium-credentials-api', (): Record<string, unknown> => ({
  usePremiumCredentialsApi: vi.fn().mockReturnValue({
    deletePremiumCredentials: vi.fn(),
    getPremiumCapabilities: vi.fn().mockResolvedValue({}),
    setPremiumCredentials: vi.fn(),
  }),
}));

describe('premium-settings', () => {
  let wrapper: VueWrapper<InstanceType<typeof PremiumSettings>>;
  let api: ReturnType<typeof usePremiumCredentialsApi>;

  function createWrapper(): VueWrapper<InstanceType<typeof PremiumSettings>> {
    const pinia = createPinia();
    setActivePinia(pinia);
    return mount(PremiumSettings, {
      global: {
        plugins: [pinia],
        stubs: ['i18n-t', 'card-title'],
        provide: libraryDefaults,
      },
    });
  }

  beforeEach((): void => {
    document.body.dataset.app = 'true';
    wrapper = createWrapper();
    api = usePremiumCredentialsApi();
  });

  afterEach((): void => {
    wrapper.unmount();
  });

  it('should update premium status upon setting keys', async () => {
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

  it('should update premium status upon removing keys', async () => {
    const premium = usePremium();
    set(premium, true);

    await nextTick();
    api.deletePremiumCredentials = vi.fn().mockResolvedValue({ result: true });

    await wrapper.find('[data-cy=premium__delete]').trigger('click');
    await nextTick();
    await flushPromises();
    await flushPromises();

    const { confirm } = useConfirmStore();
    await confirm();
    await flushPromises();

    const { premiumUserLoggedIn } = useInterop();
    expect(premiumUserLoggedIn).toHaveBeenCalledWith(false);
  });
});
