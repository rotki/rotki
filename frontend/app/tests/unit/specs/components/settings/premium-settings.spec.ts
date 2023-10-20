import { type Wrapper, mount } from '@vue/test-utils';
import flushPromises from 'flush-promises/index';
import Vuetify from 'vuetify';
import Card from '@/components/helper/Card.vue';
import PremiumSettings from '@/pages/settings/api-keys/premium/index.vue';

vi.mock('@/composables/electron-interop', () => {
  const mockInterop = {
    premiumUserLoggedIn: vi.fn()
  };
  return {
    useInterop: vi.fn().mockReturnValue(mockInterop),
    interop: mockInterop
  };
});

vi.mock('@/composables/api/session/premium-credentials', () => ({
  usePremiumCredentialsApi: vi.fn().mockReturnValue({})
}));

describe('PremiumSettings.vue', () => {
  let wrapper: Wrapper<PremiumSettings>;
  let api: ReturnType<typeof usePremiumCredentialsApi>;

  function createWrapper() {
    const vuetify = new Vuetify();
    const pinia = createPinia();
    setActivePinia(pinia);
    return mount(PremiumSettings, {
      pinia,
      vuetify,
      components: {
        Card
      },
      stubs: ['v-tooltip', 'v-dialog', 'i18n', 'card-title']
    });
  }

  beforeEach(() => {
    document.body.dataset.app = 'true';
    wrapper = createWrapper();
    api = usePremiumCredentialsApi();
  });

  test('updates premium status upon setting keys', async () => {
    api.setPremiumCredentials = vi.fn().mockResolvedValue({ result: true });
    const apiKey = wrapper.find('[data-cy=premium__api-key]');
    const apiSecret = wrapper.find('[data-cy=premium__api-secret]');

    await apiKey.setValue('1234');
    await apiSecret.setValue('1234');

    await wrapper.vm.$nextTick();
    await wrapper.find('[data-cy=premium__setup]').trigger('click');
    await wrapper.vm.$nextTick();
    await flushPromises();

    const { premiumUserLoggedIn } = useInterop();
    expect(premiumUserLoggedIn).toHaveBeenCalledWith(true);
  });

  test('updates premium status upon removing keys', async () => {
    const { premium } = storeToRefs(usePremiumStore());
    set(premium, true);

    await wrapper.vm.$nextTick();
    api.deletePremiumCredentials = vi.fn().mockResolvedValue({ result: true });

    await wrapper.find('[data-cy=premium__delete]').trigger('click');
    await wrapper.vm.$nextTick();
    await flushPromises();

    const { confirm } = useConfirmStore();
    await confirm();
    await flushPromises();

    const { premiumUserLoggedIn } = useInterop();
    expect(premiumUserLoggedIn).toHaveBeenCalledWith(false);
  });
});
