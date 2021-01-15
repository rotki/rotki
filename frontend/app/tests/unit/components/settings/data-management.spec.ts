import { mount, Wrapper } from '@vue/test-utils';
import flushPromises from 'flush-promises';
import Vue from 'vue';
import Vuetify from 'vuetify';
import DataManagement from '@/components/settings/data-security/DataManagement.vue';
import { SUPPORTED_EXCHANGES } from '@/data/defaults';
import { Api } from '@/plugins/api';
import { api } from '@/services/rotkehlchen-api';
import store from '@/store/store';
import '../../i18n';

jest.mock('@/services/rotkehlchen-api');

Vue.use(Vuetify);
Vue.use(Api);

describe('DataManagement.vue', () => {
  let wrapper: Wrapper<DataManagement>;

  function createWrapper() {
    const vuetify = new Vuetify();
    return mount(DataManagement, {
      store,
      vuetify,
      stubs: {
        VDialog: {
          template: '<span v-if="value"><slot></slot></span>',
          props: {
            value: { type: Boolean }
          }
        }
      }
    });
  }

  beforeEach(() => {
    jest.resetAllMocks();
    jest.useFakeTimers();
    (api.balances as any) = jest.mock('@/services/balances/balances-api');
    wrapper = createWrapper();
  });

  afterEach(() => {
    jest.useRealTimers();
  });

  test('purges ethereum transactions', async () => {
    api.balances.deleteEthereumTransactions = jest.fn().mockResolvedValue(true);
    wrapper
      .find('.data-management__purge-transactions button')
      .trigger('click');
    await wrapper.vm.$nextTick();
    wrapper.find('.confirm-dialog__buttons__confirm').trigger('click');
    await wrapper.vm.$nextTick();
    await flushPromises();
    expect(
      wrapper.find('.status-button__message--success').element
    ).toBeVisible();
    jest.advanceTimersByTime(5000);
    await wrapper.vm.$nextTick();
    expect(
      wrapper.find('.data-management__transactions__message').exists()
    ).toBe(false);
    expect(api.balances.deleteEthereumTransactions).toHaveBeenCalledWith();
  });

  test('fails to purge ethereum transactions', async () => {
    api.balances.deleteEthereumTransactions = jest
      .fn()
      .mockRejectedValue(new Error('failed'));
    wrapper
      .find('.data-management__purge-transactions button')
      .trigger('click');
    await wrapper.vm.$nextTick();
    wrapper.find('.confirm-dialog__buttons__confirm').trigger('click');
    await wrapper.vm.$nextTick();
    await flushPromises();
    const message = wrapper.find('.status-button__message--error');
    expect(message.element).toBeVisible();
    expect(message.classes()).toContain('error--text');
  });

  test('purges all exchange cached data', async () => {
    api.balances.deleteExchangeData = jest.fn().mockResolvedValue(true);
    wrapper
      .find('.data-management__purge-all-exchange button')
      .trigger('click');
    await wrapper.vm.$nextTick();
    wrapper.find('.confirm-dialog__buttons__confirm').trigger('click');
    await wrapper.vm.$nextTick();
    await flushPromises();
    expect(
      wrapper.find('.status-button__message--success').element
    ).toBeVisible();
    jest.advanceTimersByTime(5000);
    await wrapper.vm.$nextTick();
    expect(
      wrapper.find('.data-management__transactions__message').exists()
    ).toBe(false);
    expect(api.balances.deleteExchangeData).toHaveBeenCalledWith();
  });

  test('fails to purge all exchange cached data', async () => {
    api.balances.deleteExchangeData = jest
      .fn()
      .mockRejectedValue(new Error('failed'));
    wrapper
      .find('.data-management__purge-all-exchange button')
      .trigger('click');
    await wrapper.vm.$nextTick();
    wrapper.find('.confirm-dialog__buttons__confirm').trigger('click');
    await wrapper.vm.$nextTick();
    await flushPromises();
    const message = wrapper.find('.status-button__message--error');
    expect(message.element).toBeVisible();
    expect(message.classes()).toContain('error--text');
  });

  test('purges exchange data', async () => {
    wrapper.find('.data-management__purge-exchange').trigger('click');
    await wrapper.vm.$nextTick();
    wrapper.find('.confirm-dialog__buttons__confirm').trigger('click');
    await wrapper.vm.$nextTick();
    await flushPromises();
    expect(
      wrapper.find('.data-management__fields__exchange').classes()
    ).toContain('success--text');
    jest.advanceTimersByTime(5000);
    await wrapper.vm.$nextTick();
    expect(
      wrapper.find('.data-management__fields__exchange').classes()
    ).not.toContain('success--text');
    expect(api.balances.deleteExchangeData).toHaveBeenCalledWith(
      SUPPORTED_EXCHANGES[0]
    );
  });

  test('fails to purge exchange data', async () => {
    api.balances.deleteExchangeData = jest
      .fn()
      .mockRejectedValue(new Error('failure'));
    wrapper.find('.data-management__purge-exchange').trigger('click');
    await wrapper.vm.$nextTick();
    wrapper.find('.confirm-dialog__buttons__confirm').trigger('click');
    await wrapper.vm.$nextTick();
    await flushPromises();
    expect(
      wrapper.find('.data-management__fields__exchange').classes()
    ).toContain('error--text');
  });
});
