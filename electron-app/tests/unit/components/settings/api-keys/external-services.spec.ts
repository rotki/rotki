import { mount, Wrapper } from '@vue/test-utils';
import flushPromises from 'flush-promises';
import Vue from 'vue';
import Vuetify from 'vuetify';
import ExternalServices from '@/components/settings/api-keys/ExternalServices.vue';
import { ExternalServiceKeys } from '@/model/action-result';
import store from '@/store/store';

Vue.use(Vuetify);

describe('ExternalServices.vue', () => {
  let vuetify: typeof Vuetify;
  let wrapper: Wrapper<ExternalServices>;
  let queryExternalServices: jest.Mock;
  let setExternalServices: jest.Mock;
  let deleteExternalServices: jest.Mock;

  const mockResponse: ExternalServiceKeys = {
    etherscan: {
      api_key: '123'
    },
    cryptocompare: {
      api_key: '123'
    }
  };

  function createWrapper(): Wrapper<ExternalServices> {
    vuetify = new Vuetify();
    return mount(ExternalServices, {
      store,
      vuetify,
      stubs: ['v-dialog'],
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
    queryExternalServices = jest.fn();
    setExternalServices = jest.fn();
    deleteExternalServices = jest.fn();
    vuetify = new Vuetify();
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
        { name: 'etherscan', api_key: '123' }
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
      expect(store.state.message.description).toMatch('cryptocompare');
      expect(setExternalServices).toHaveBeenCalledWith([
        { name: 'cryptocompare', api_key: '123' }
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
      expect(store.state.message.description).toMatch('mock failure');
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

      wrapper.find('.confirm-dialog__buttons__confirm').trigger('click');
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

      wrapper.find('.confirm-dialog__buttons__confirm').trigger('click');
      await wrapper.vm.$nextTick();
      await flushPromises();

      expect(deleteExternalServices).toHaveBeenCalledWith('cryptocompare');

      // @ts-ignore
      expect(wrapper.vm.serviceToDelete).toBe('');
      expect(store.state.message.description).toMatch('mock failure');
    });
  });
});
