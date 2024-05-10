import { type Wrapper, mount } from '@vue/test-utils';
import flushPromises from 'flush-promises/index';
import Vuetify from 'vuetify';
import PremiumSettings from '@/pages/settings/api-keys/premium/index.vue';

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
  let wrapper: Wrapper<PremiumSettings>;
  let api: ReturnType<typeof usePremiumCredentialsApi>;

  function createWrapper() {
    const vuetify = new Vuetify();
    const pinia = createPinia();
    setActivePinia(pinia);
    return mount(PremiumSettings, {
      pinia,
      vuetify,
      stubs: ['i18n', 'card-title'],
    });
  }

  beforeEach(() => {
    document.body.dataset.app = 'true';
    wrapper = createWrapper();
    api = usePremiumCredentialsApi();
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
    const { premium } = storeToRefs(usePremiumStore());
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
