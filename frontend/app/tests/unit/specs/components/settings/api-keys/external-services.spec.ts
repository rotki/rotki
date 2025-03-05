import { type VueWrapper, mount } from '@vue/test-utils';
import flushPromises from 'flush-promises';
import { type Pinia, setActivePinia } from 'pinia';
import { computed } from 'vue';
import { Blockchain } from '@rotki/common';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { createCustomPinia } from '@test/utils/create-pinia';
import ExternalServices from '@/pages/api-keys/external/index.vue';
import EvmChainIcon from '@/components/helper/display/icons/EvmChainIcon.vue';
import ServiceKey from '@/components/settings/api-keys/ServiceKey.vue';
import { useConfirmStore } from '@/store/confirm';
import { useExternalServicesApi } from '@/composables/api/settings/external-services-api';
import ServiceKeyCard from '@/components/settings/api-keys/ServiceKeyCard.vue';
import ServiceWithAuth from '@/components/settings/api-keys/ServiceWithAuth.vue';
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

vi.mock('vue-router', () => ({
  useRoute: vi.fn().mockImplementation(() => ref({ hash: '' })),
  useRouter: vi.fn(),
  createRouter: vi.fn().mockImplementation(() => ({
    beforeEach: vi.fn(),
  })),
  createWebHashHistory: vi.fn(),
}));

vi.mock('@/composables/api/settings/external-services-api', () => ({
  useExternalServicesApi: vi.fn().mockReturnValue({
    queryExternalServices: vi.fn(),
    setExternalServices: vi.fn(),
    deleteExternalServices: vi.fn(),
  }),
}));

describe('/settings/api-keys/external-services', () => {
  let wrapper: VueWrapper<InstanceType<typeof ExternalServices>>;
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

  function createWrapper(): VueWrapper<InstanceType<typeof ExternalServices>> {
    return mount(ExternalServices, {
      global: {
        plugins: [pinia],
        stubs: {
          RouterLink: true,
          RuiTabs: true,
          Transition: {
            template: '<span><slot /></span>',
          },
          Teleport: {
            template: '<span><slot /></span>',
          },
          EvmChainIcon,
          ServiceKeyCard,
          ServiceKey,
          ServiceWithAuth,
        },
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
    wrapper.unmount();
  });

  describe('first time', () => {
    beforeEach(async () => {
      const query = api.queryExternalServices as any;
      query.mockResolvedValueOnce({
        etherscan: {
          ethereum: null,
        },
      });
      wrapper = createWrapper();
      await vi.dynamicImportSettled();
      await nextTick();
      await flushPromises();
    });

    it('save the values when etherscan save is pressed', async () => {
      const mock = vi.mocked(api.setExternalServices);
      mock.mockResolvedValueOnce(mockResponse);
      await wrapper
        .find('[data-cy=external-keys] [data-cy=etherscan-api-keys] button')
        .trigger('click');
      await vi.advanceTimersToNextTimerAsync();
      await wrapper
        .find('[data-cy="bottom-dialog"] [data-cy=etherscan] [data-cy=service-key__api-key] input')
        .setValue('123');
      await nextTick();
      await wrapper.find('[data-cy="bottom-dialog"] [data-cy=etherscan] [data-cy=service-key__save]').trigger('click');
      await flushPromises();
      await vi.advanceTimersToNextTimerAsync();
      expect(mock).toHaveBeenCalledWith([{ name: 'etherscan', apiKey: '123' }]);
    });

    it('save the values when cryptocompare save is pressed', async () => {
      const mock = vi.mocked(api.setExternalServices);
      mock.mockResolvedValueOnce(mockResponse);
      await wrapper
        .find('[data-cy=external-keys] [data-cy=cryptocompare-api-keys] button')
        .trigger('click');
      await vi.advanceTimersToNextTimerAsync();
      await wrapper
        .find('[data-cy="bottom-dialog"] [data-cy=cryptocompare] [data-cy=service-key__api-key] input')
        .setValue('123');
      await nextTick();
      await wrapper.find('[data-cy="bottom-dialog"] [data-cy="confirm"]').trigger('click');
      await flushPromises();
      const message = wrapper
        .find('[data-cy="bottom-dialog"] [data-cy=cryptocompare] [data-cy=service-key__content] .details')
        .text();
      expect(message).toMatch('Cryptocompare');
      await vi.advanceTimersToNextTimerAsync();
      expect(mock).toHaveBeenCalledWith([{ name: 'cryptocompare', apiKey: '123' }]);
    });

    it('save fails with an error', async () => {
      const mock = vi.mocked(api.setExternalServices);
      mock.mockRejectedValueOnce(new Error('mock failure'));
      await wrapper
        .find('[data-cy=external-keys] [data-cy=etherscan-api-keys] button')
        .trigger('click');
      await vi.advanceTimersToNextTimerAsync();
      await wrapper
        .find('[data-cy=bottom-dialog] [data-cy=etherscan] [data-cy=service-key__api-key] input')
        .setValue('123');
      await nextTick();
      await wrapper.find('[data-cy=bottom-dialog] [data-cy=etherscan] [data-cy=service-key__save]').trigger('click');
      await flushPromises();
      const message = wrapper
        .find('[data-cy=bottom-dialog] [data-cy=etherscan] [data-cy=service-key__content] .details')
        .text();
      expect(message).toMatch('mock failure');
      await vi.advanceTimersToNextTimerAsync();
    });

    it('delete is disabled', async () => {
      await wrapper
        .find('[data-cy=external-keys] [data-cy=etherscan-api-keys] button')
        .trigger('click');
      await vi.advanceTimersToNextTimerAsync();
      expect(
        wrapper.find('[data-cy=bottom-dialog] [data-cy=etherscan] [data-cy=service-key__delete]').attributes(),
      ).toHaveProperty('disabled');

      // Close the dialog
      await wrapper
        .find('[data-cy=bottom-dialog] [data-cy=cancel]')
        .trigger('click');
      await vi.advanceTimersToNextTimerAsync();

      await wrapper
        .find('[data-cy=external-keys] [data-cy=cryptocompare-api-keys] button')
        .trigger('click');
      await vi.advanceTimersToNextTimerAsync();

      expect(
        wrapper.find('[data-cy=bottom-dialog] [data-cy=delete-button]').attributes(),
      ).toHaveProperty('disabled');
    });

    it('save is disabled', async () => {
      await wrapper
        .find('[data-cy=external-keys] [data-cy=etherscan-api-keys] button')
        .trigger('click');
      await vi.advanceTimersToNextTimerAsync();
      expect(
        wrapper.find('[data-cy=bottom-dialog] [data-cy=etherscan] [data-cy=service-key__save]').attributes(),
      ).toHaveProperty('disabled');
    });
  });

  describe('the api returns value', () => {
    beforeEach(async () => {
      vi.mocked(api.queryExternalServices).mockResolvedValueOnce(mockResponse);
      wrapper = createWrapper();
      await vi.dynamicImportSettled();
      await nextTick();
      await flushPromises();
    });

    it('the fields get updated', async () => {
      await wrapper
        .find('[data-cy=external-keys] [data-cy=etherscan-api-keys] button')
        .trigger('click');
      await vi.advanceTimersToNextTimerAsync();

      const etherscanKey = wrapper.find('[data-cy=bottom-dialog] [data-cy=etherscan]').findComponent(ServiceKey);
      expect(etherscanKey.vm.apiKey).toBe('123');

      // Close the dialog
      await wrapper
        .find('[data-cy=bottom-dialog] [data-cy=cancel]')
        .trigger('click');
      await vi.advanceTimersToNextTimerAsync();

      await wrapper
        .find('[data-cy=external-keys] [data-cy=cryptocompare-api-keys] button')
        .trigger('click');
      await vi.advanceTimersToNextTimerAsync();

      const cryptoCompare = wrapper.find('[data-cy=bottom-dialog] [data-cy=cryptocompare]').findComponent(ServiceKey);

      expect(etherscanKey.vm.apiKey).toBe('123');
      expect(cryptoCompare.vm.apiKey).toBe('123');
    });

    it('confirm and delete etherscan key', async () => {
      const mock = vi.mocked(api.deleteExternalServices);
      mock.mockResolvedValueOnce({});

      await wrapper
        .find('[data-cy=external-keys] [data-cy=etherscan-api-keys] button')
        .trigger('click');
      await vi.advanceTimersToNextTimerAsync();

      await wrapper.find('[data-cy=bottom-dialog] [data-cy=etherscan] [data-cy=service-key__delete]').trigger('click');
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
        .find('[data-cy=external-keys] [data-cy=cryptocompare-api-keys] button')
        .trigger('click');
      await vi.advanceTimersToNextTimerAsync();

      await wrapper
        .find('[data-cy=bottom-dialog] [data-cy=delete-button]')
        .trigger('click');
      await nextTick();

      const confirmStore = useConfirmStore();
      await confirmStore.confirm();
      await nextTick();
      await flushPromises();

      expect(mock).toHaveBeenCalledWith('cryptocompare');
      expect(confirmStore.visible).toBeFalsy();

      const message = wrapper
        .find('[data-cy=bottom-dialog] [data-cy=cryptocompare] [data-cy=service-key__content] .details')
        .text();
      expect(message).toMatch('mock failure');
    });
  });
});
