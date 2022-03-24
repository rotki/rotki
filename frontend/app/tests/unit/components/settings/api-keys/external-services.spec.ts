import { mount, Wrapper } from '@vue/test-utils';
import flushPromises from 'flush-promises';
import { createPinia, Pinia, setActivePinia } from 'pinia';
import Vue from 'vue';
import Vuetify from 'vuetify';
import ExternalServices from '@/components/settings/api-keys/ExternalServices.vue';
import store, { useMainStore } from '@/store/store';
import '../../../i18n';
import { ExternalServiceKeys } from '@/types/user';

Vue.use(Vuetify);

describe('ExternalServices.vue', () => {
  let wrapper: Wrapper<ExternalServices>;
  let queryExternalServices: any;
  let setExternalServices: any;
  let deleteExternalServices: any;
  let pinia: Pinia;

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
      store,
      pinia,
      vuetify,
      stubs: ['v-dialog', 'card-title', 'card'],
      propsData: {
        value: ''
      },
      mocks: {
        $api: {
          queryExternalServices,
          setExternalServices,
          deleteExternalServices
        }
      }
    });
  }

  beforeEach(() => {
    pinia = createPinia();
    setActivePinia(pinia);
    queryExternalServices = vi.fn();
    setExternalServices = vi.fn();
    deleteExternalServices = vi.fn();
  });

  afterEach(() => {
    store.commit('session/reset');
  });

  describe('first time', () => {
    beforeEach(async () => {
      queryExternalServices.mockResolvedValueOnce({} as ExternalServiceKeys);
      wrapper = createWrapper();
      await wrapper.vm.$nextTick();
      await flushPromises();
    });

    test('save the values when etherscan save is pressed', async () => {
      setExternalServices.mockResolvedValueOnce(mockResponse);
      wrapper.find('.external-services__etherscan-key input').setValue('123');
      await wrapper.vm.$nextTick();
      wrapper
        .find('.external-services__etherscan-key .service-key__buttons__save')
        .trigger('click');
      await flushPromises();
      expect(setExternalServices).toHaveBeenCalledWith([
        { name: 'etherscan', apiKey: '123' }
      ]);
    });

    test('save the values when cryptocompare save is pressed', async () => {
      setExternalServices.mockResolvedValueOnce(mockResponse);
      wrapper
        .find('.external-services__cryptocompare-key input')
        .setValue('123');
      await wrapper.vm.$nextTick();
      wrapper
        .find(
          '.external-services__cryptocompare-key .service-key__buttons__save'
        )
        .trigger('click');
      await flushPromises();
      const store = useMainStore();
      expect(store.message.description).toMatch('cryptocompare');
      expect(setExternalServices).toHaveBeenCalledWith([
        { name: 'cryptocompare', apiKey: '123' }
      ]);
    });

    test('save fails with an error', async () => {
      setExternalServices.mockRejectedValueOnce(new Error('mock failure'));
      wrapper.find('.external-services__etherscan-key input').setValue('123');
      await wrapper.vm.$nextTick();
      wrapper
        .find('.external-services__etherscan-key .service-key__buttons__save')
        .trigger('click');
      await flushPromises();
      const store = useMainStore();
      expect(store.message.description).toMatch('mock failure');
    });

    test('delete is disabled', async () => {
      expect(
        wrapper
          .find(
            '.external-services__etherscan-key .service-key__content__delete'
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
          .find('.external-services__etherscan-key .service-key__buttons__save')
          .attributes('disabled')
      ).toBe('disabled');
    });
  });

  describe('the api returns value', () => {
    beforeEach(async () => {
      queryExternalServices.mockResolvedValueOnce(mockResponse);
      wrapper = createWrapper();
      await wrapper.vm.$nextTick();
      await flushPromises();
    });

    test('the fields get updated', async () => {
      const etherscanKey = wrapper.find('.external-services__etherscan-key');
      const cryptoCompare = wrapper.find(
        '.external-services__cryptocompare-key'
      );
      // @ts-ignore
      expect(etherscanKey.vm.value).toBe('123');
      // @ts-ignore
      expect(cryptoCompare.vm.value).toBe('123');
    });

    test('confirm and delete etherscan key', async () => {
      deleteExternalServices.mockResolvedValueOnce({});
      wrapper
        .find('.external-services__etherscan-key .service-key__content__delete')
        .trigger('click');
      await wrapper.vm.$nextTick();

      // @ts-ignore
      expect(wrapper.vm.serviceToDelete).toBe('etherscan');

      wrapper
        .find('[data-cy="confirm-dialog"] [data-cy="button-confirm"]')
        .trigger('click');
      await wrapper.vm.$nextTick();
      await flushPromises();

      expect(deleteExternalServices).toHaveBeenCalledWith('etherscan');

      // @ts-ignore
      expect(wrapper.vm.serviceToDelete).toBe('');
    });

    test('delete cryptocompare fails', async () => {
      deleteExternalServices.mockRejectedValueOnce(new Error('mock failure'));
      wrapper
        .find(
          '.external-services__cryptocompare-key .service-key__content__delete'
        )
        .trigger('click');
      await wrapper.vm.$nextTick();

      // @ts-ignore
      expect(wrapper.vm.serviceToDelete).toBe('cryptocompare');

      wrapper
        .find('[data-cy="confirm-dialog"] [data-cy="button-confirm"]')
        .trigger('click');
      await wrapper.vm.$nextTick();
      await flushPromises();

      expect(deleteExternalServices).toHaveBeenCalledWith('cryptocompare');

      // @ts-ignore
      expect(wrapper.vm.serviceToDelete).toBe('');
      const store = useMainStore();
      expect(store.message.description).toMatch('mock failure');
    });
  });
});
