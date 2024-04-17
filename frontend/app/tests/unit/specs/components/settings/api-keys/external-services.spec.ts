import { type Wrapper, mount } from '@vue/test-utils';
import flushPromises from 'flush-promises';
import { type Pinia, setActivePinia } from 'pinia';
import Vuetify from 'vuetify';
import { computed, reactive } from 'vue';
import { Blockchain } from '@rotki/common/lib/blockchain';
import ExternalServices from '@/pages/settings/api-keys/external/index.vue';
import EvmChainIcon from '@/components/helper/display/icons/EvmChainIcon.vue';
import { createCustomPinia } from '../../../../utils/create-pinia';
import type { ExternalServiceKeys } from '@/types/user';
import type { EvmChainInfo } from '@/types/api/chains';

vi.mock('@/composables/info/chains', () => ({
  useSupportedChains: vi.fn().mockReturnValue({
    txEvmChains: computed(() => [
      {
        evmChainName: 'ethereum',
        id: Blockchain.ETH,
        type: 'evm',
        name: 'Ethereum',
        image: '',
        nativeToken: 'ETH',
      } satisfies EvmChainInfo,
    ]),
    getChain: () => Blockchain.ETH,
    getChainName: () => 'Ethereum',
    getNativeAsset: (chain: Blockchain) => chain,
    getChainImageUrl: (chain: Blockchain) => `${chain}.png`,
  }),
}));

vi.mock('vue-router/composables', () => ({
  useRoute: vi.fn().mockReturnValue(
    reactive({
      hash: '',
    }),
  ),
  useRouter: vi.fn(),
}));

vi.mock('@/composables/api/settings/external-services-api', () => ({
  useExternalServicesApi: vi.fn().mockReturnValue({
    queryExternalServices: vi.fn(),
    setExternalServices: vi.fn(),
    deleteExternalServices: vi.fn(),
  }),
}));

describe('/settings/api-keys/external-services', () => {
  let wrapper: Wrapper<ExternalServices>;
  let pinia: Pinia;
  let api: ReturnType<typeof useExternalServicesApi>;

  const mockResponse: ExternalServiceKeys = {
    etherscan: {
      ethereum: {
        apiKey: '123',
      },
    },
    cryptocompare: {
      apiKey: '123',
    },
  };

  function createWrapper(): Wrapper<ExternalServices> {
    const vuetify = new Vuetify();
    return mount(ExternalServices, {
      pinia,
      vuetify,
      components: {
        EvmChainIcon,
      },
      stubs: ['RuiTabs'],
      propsData: {
        value: '',
      },
    });
  }

  beforeEach(() => {
    document.body.dataset.app = 'true';
    pinia = createCustomPinia();
    setActivePinia(pinia);
    api = useExternalServicesApi();
    vi.useFakeTimers();
  });

  afterEach(() => {
    useSessionStore().$reset();
    wrapper.destroy();
  });

  describe('first time', () => {
    beforeEach(async () => {
      const query = api.queryExternalServices as any;
      query.mockResolvedValueOnce({});
      wrapper = createWrapper();
      await nextTick();
      await flushPromises();
    });

    it('save the values when etherscan save is pressed', async () => {
      const mock = vi.mocked(api.setExternalServices);
      mock.mockResolvedValueOnce(mockResponse);
      await wrapper
        .find(
          '[data-cy=external-keys] [data-cy=etherscan] [data-cy=service-key__api-key] input',
        )
        .setValue('123');
      await nextTick();
      await wrapper
        .find(
          '[data-cy=external-keys] [data-cy=etherscan] [data-cy=service-key__save]',
        )
        .trigger('click');
      await flushPromises();
      await vi.advanceTimersToNextTimerAsync();
      expect(mock).toHaveBeenCalledWith([{ name: 'etherscan', apiKey: '123' }]);
    });

    it('save the values when cryptocompare save is pressed', async () => {
      const mock = vi.mocked(api.setExternalServices);
      mock.mockResolvedValueOnce(mockResponse);
      await wrapper
        .find(
          '[data-cy=external-keys] [data-cy=cryptocompare] [data-cy=service-key__api-key] input',
        )
        .setValue('123');
      await nextTick();
      await wrapper
        .find(
          '[data-cy=external-keys] [data-cy=cryptocompare] [data-cy=service-key__save]',
        )
        .trigger('click');
      await flushPromises();
      const message = wrapper
        .find(
          '[data-cy=external-keys] [data-cy=cryptocompare] [data-cy=service-key__content] .details',
        )
        .text();
      expect(message).toMatch('Cryptocompare');
      await vi.advanceTimersToNextTimerAsync();
      expect(mock).toHaveBeenCalledWith([
        { name: 'cryptocompare', apiKey: '123' },
      ]);
    });

    it('save fails with an error', async () => {
      const mock = vi.mocked(api.setExternalServices);
      mock.mockRejectedValueOnce(new Error('mock failure'));
      await wrapper
        .find(
          '[data-cy=external-keys] [data-cy=etherscan] [data-cy=service-key__api-key] input',
        )
        .setValue('123');
      await nextTick();
      await wrapper
        .find(
          '[data-cy=external-keys] [data-cy=etherscan] [data-cy=service-key__save]',
        )
        .trigger('click');
      await flushPromises();
      const message = wrapper
        .find(
          '[data-cy=external-keys] [data-cy=etherscan] [data-cy=service-key__content] .details',
        )
        .text();
      expect(message).toMatch('mock failure');
      await vi.advanceTimersToNextTimerAsync();
    });

    it('delete is disabled', () => {
      expect(
        wrapper
          .find(
            '[data-cy=external-keys] [data-cy=etherscan] [data-cy=service-key__delete]',
          )
          .attributes('disabled'),
      ).toBe('disabled');
      expect(
        wrapper
          .find(
            '[data-cy=external-keys] [data-cy=cryptocompare] [data-cy=service-key__delete]',
          )
          .attributes('disabled'),
      ).toBe('disabled');
    });

    it('save is disabled', () => {
      expect(
        wrapper
          .find(
            '[data-cy=external-keys] [data-cy=etherscan] [data-cy=service-key__save]',
          )
          .attributes('disabled'),
      ).toBe('disabled');
    });
  });

  describe('the api returns value', () => {
    beforeEach(async () => {
      vi.mocked(api.queryExternalServices).mockResolvedValueOnce(mockResponse);
      wrapper = createWrapper();
      await nextTick();
      await flushPromises();
    });

    it('the fields get updated', () => {
      const etherscanKey = wrapper.find(
        '[data-cy=external-keys] [data-cy=etherscan]',
      );
      const cryptoCompare = wrapper.find(
        '[data-cy=external-keys] [data-cy=cryptocompare]',
      );

      expect(etherscanKey.vm.$children[0].$props.apiKey).toBe('123');
      expect(cryptoCompare.vm.$props.apiKey).toBe('123');
    });

    it('confirm and delete etherscan key', async () => {
      const mock = vi.mocked(api.deleteExternalServices);
      mock.mockResolvedValueOnce({});
      await wrapper
        .find(
          '[data-cy=external-keys] [data-cy=etherscan] [data-cy=service-key__delete]',
        )
        .trigger('click');
      await nextTick();

      const confirmStore = useConfirmStore();
      await confirmStore.confirm();
      await nextTick();
      await flushPromises();

      expect(mock).toHaveBeenCalledWith('etherscan');
      expect(confirmStore.visible).toBeFalsy();
    });

    it('delete cryptocompare fails', async () => {
      const mock = vi.mocked(api.deleteExternalServices);
      mock.mockRejectedValueOnce(new Error('mock failure'));
      await wrapper
        .find(
          '[data-cy=external-keys] [data-cy=cryptocompare] [data-cy=service-key__delete]',
        )
        .trigger('click');
      await nextTick();

      const confirmStore = useConfirmStore();
      await confirmStore.confirm();
      await nextTick();
      await flushPromises();

      expect(mock).toHaveBeenCalledWith('cryptocompare');
      expect(confirmStore.visible).toBeFalsy();

      const message = wrapper
        .find(
          '[data-cy=external-keys] [data-cy=cryptocompare] [data-cy=service-key__content] .details',
        )
        .text();
      expect(message).toMatch('mock failure');
    });
  });
});
