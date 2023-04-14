import { type Wrapper, mount } from '@vue/test-utils';
import flushPromises from 'flush-promises';
import { type Pinia, setActivePinia } from 'pinia';
import Vuetify from 'vuetify';
import { reactive } from 'vue';
import ExternalServices from '@/pages/settings/api-keys/external/index.vue';
import { type ExternalServiceKeys } from '@/types/user';
import EvmChainIcon from '@/components/helper/display/icons/EvmChainIcon.vue';
import createCustomPinia from '../../../../utils/create-pinia';

vi.mock('vue-router/composables', () => ({
  useRoute: vi.fn().mockReturnValue(
    reactive({
      hash: ''
    })
  )
}));

vi.mock('@/composables/api/settings/external-services-api', () => ({
  useExternalServicesApi: vi.fn().mockReturnValue({
    queryExternalServices: vi.fn(),
    setExternalServices: vi.fn(),
    deleteExternalServices: vi.fn()
  })
}));

describe('ExternalServices.vue', () => {
  let wrapper: Wrapper<ExternalServices>;
  let pinia: Pinia;
  let api: ReturnType<typeof useExternalServicesApi>;

  const mockResponse: ExternalServiceKeys = {
    etherscan: {
      apiKey: '123'
    },
    cryptocompare: {
      apiKey: '123'
    }
  };

  function createWrapper(): Wrapper<ExternalServices> {
    const vuetify = new Vuetify();
    return mount(ExternalServices, {
      pinia,
      vuetify,
      components: {
        EvmChainIcon
      },
      stubs: ['v-dialog', 'card-title', 'card', 'i18n'],
      propsData: {
        value: ''
      }
    });
  }

  beforeEach(() => {
    document.body.dataset.app = 'true';
    pinia = createCustomPinia();
    setActivePinia(pinia);
    api = useExternalServicesApi();
  });

  afterEach(() => {
    useSessionStore().$reset();
  });

  describe('first time', () => {
    beforeEach(async () => {
      const query = api.queryExternalServices as any;
      query.mockResolvedValueOnce({});
      wrapper = createWrapper();
      await wrapper.vm.$nextTick();
      await flushPromises();
    });

    test('save the values when etherscan save is pressed', async () => {
      const setService = api.setExternalServices as any;
      setService.mockResolvedValueOnce(mockResponse);
      await wrapper
        .find('.external-services__ethereum-etherscan-key input')
        .setValue('123');
      await wrapper.vm.$nextTick();
      await wrapper
        .find(
          '.external-services__ethereum-etherscan-key .service-key__buttons__save'
        )
        .trigger('click');
      await flushPromises();
      expect(setService).toHaveBeenCalledWith([
        { name: 'etherscan', apiKey: '123' }
      ]);
    });

    test('save the values when cryptocompare save is pressed', async () => {
      const setService = api.setExternalServices as any;
      setService.mockResolvedValueOnce(mockResponse);
      await wrapper
        .find('.external-services__cryptocompare-key input')
        .setValue('123');
      await wrapper.vm.$nextTick();
      await wrapper
        .find(
          '.external-services__cryptocompare-key .service-key__buttons__save'
        )
        .trigger('click');
      await flushPromises();
      const store = useMessageStore();
      expect(store.message.description).toMatch('Cryptocompare');
      expect(setService).toHaveBeenCalledWith([
        { name: 'cryptocompare', apiKey: '123' }
      ]);
    });

    test('save fails with an error', async () => {
      const setService = api.setExternalServices as any;
      setService.mockRejectedValueOnce(new Error('mock failure'));
      await wrapper
        .find('.external-services__ethereum-etherscan-key input')
        .setValue('123');
      await wrapper.vm.$nextTick();
      await wrapper
        .find(
          '.external-services__ethereum-etherscan-key .service-key__buttons__save'
        )
        .trigger('click');
      await flushPromises();
      const store = useMessageStore();
      expect(store.message.description).toMatch('mock failure');
    });

    test('delete is disabled', async () => {
      expect(
        wrapper
          .find(
            '.external-services__ethereum-etherscan-key .service-key__content__delete'
          )
          .attributes('disabled')
      ).toBe('disabled');
      expect(
        wrapper
          .find(
            '.external-services__cryptocompare-key .service-key__content__delete'
          )
          .attributes('disabled')
      ).toBe('disabled');
    });

    test('save is disabled', async () => {
      expect(
        wrapper
          .find(
            '.external-services__ethereum-etherscan-key .service-key__buttons__save'
          )
          .attributes('disabled')
      ).toBe('disabled');
    });
  });

  describe('the api returns value', () => {
    beforeEach(async () => {
      const query = api.queryExternalServices as any;
      query.mockResolvedValueOnce(mockResponse);
      wrapper = createWrapper();
      await wrapper.vm.$nextTick();
      await flushPromises();
    });

    test('the fields get updated', async () => {
      const etherscanKey = wrapper.find(
        '.external-services__ethereum-etherscan-key'
      );
      const cryptoCompare = wrapper.find(
        '.external-services__cryptocompare-key'
      );
      // @ts-ignore
      expect(etherscanKey.vm.value).toBe('123');
      // @ts-ignore
      expect(cryptoCompare.vm.value).toBe('123');
    });

    test('confirm and delete etherscan key', async () => {
      const deleteService = api.deleteExternalServices as any;
      deleteService.mockResolvedValueOnce({});
      await wrapper
        .find(
          '.external-services__ethereum-etherscan-key .service-key__content__delete'
        )
        .trigger('click');
      await wrapper.vm.$nextTick();

      const confirmStore = useConfirmStore();
      await confirmStore.confirm();
      await wrapper.vm.$nextTick();
      await flushPromises();

      expect(deleteService).toHaveBeenCalledWith('etherscan');
      expect(confirmStore.visible).toBeFalsy();
    });

    test('delete cryptocompare fails', async () => {
      const deleteService = api.deleteExternalServices as any;
      deleteService.mockRejectedValueOnce(new Error('mock failure'));
      await wrapper
        .find(
          '.external-services__cryptocompare-key .service-key__content__delete'
        )
        .trigger('click');
      await wrapper.vm.$nextTick();

      const confirmStore = useConfirmStore();
      await confirmStore.confirm();
      await wrapper.vm.$nextTick();
      await flushPromises();

      expect(deleteService).toHaveBeenCalledWith('cryptocompare');
      expect(confirmStore.visible).toBeFalsy();

      const store = useMessageStore();
      expect(store.message.description).toMatch('mock failure');
    });
  });
});
