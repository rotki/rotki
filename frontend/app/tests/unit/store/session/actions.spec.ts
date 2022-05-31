import { createPinia, setActivePinia } from 'pinia';
import { api } from '@/services/rotkehlchen-api';
import {
  QueriedAddresses,
  QueriedAddressPayload
} from '@/services/session/types';
import store, { useMainStore } from '@/store/store';
import { Module } from '@/types/modules';

vi.mock('@/services/rotkehlchen-api');

describe('session:actions', () => {
  beforeEach(() => {
    const pinia = createPinia();
    setActivePinia(pinia);
    store.dispatch('session/logout');
  });

  test('fetchQueriedAddresses', async () => {
    expect.assertions(2);
    const response: QueriedAddresses = {
      makerdao_dsr: ['0x52bc44d5378309EE2abF1539BF71dE1b7d7bE3b5']
    };
    api.session.queriedAddresses = vi.fn().mockResolvedValue(response);
    await store.dispatch('session/fetchQueriedAddresses');
    expect(api.session.queriedAddresses).toHaveBeenCalledTimes(1);
    expect(store.state.session!.queriedAddresses).toMatchObject(response);
  });

  test('fetchQueriedAddresses fails', async () => {
    expect.assertions(3);
    api.session.queriedAddresses = vi
      .fn()
      .mockRejectedValue(new Error('failed'));
    await store.dispatch('session/fetchQueriedAddresses');
    expect(api.session.queriedAddresses).toHaveBeenCalledTimes(1);
    expect(store.state.session!.queriedAddresses).toMatchObject({});
    expect(useMainStore().message.description).toBeTruthy();
  });

  test('addQueriedAddress', async () => {
    expect.assertions(2);
    const payload: QueriedAddressPayload = {
      module: Module.MAKERDAO_DSR,
      address: '0x52bc44d5378309EE2abF1539BF71dE1b7d7bE3b5'
    };
    const response: QueriedAddresses = {
      makerdao_dsr: ['0x52bc44d5378309EE2abF1539BF71dE1b7d7bE3b5']
    };
    api.session.addQueriedAddress = vi.fn().mockResolvedValue(response);
    await store.dispatch('session/addQueriedAddress', payload);
    expect(api.session.addQueriedAddress).toHaveBeenCalledWith(payload);
    expect(store.state.session!.queriedAddresses).toMatchObject(response);
  });

  test('addQueriedAddress fails', async () => {
    expect.assertions(3);
    const payload: QueriedAddressPayload = {
      module: Module.MAKERDAO_DSR,
      address: '0x52bc44d5378309EE2abF1539BF71dE1b7d7bE3b5'
    };

    api.session.addQueriedAddress = vi
      .fn()
      .mockRejectedValue(new Error('failed'));
    await store.dispatch('session/addQueriedAddress', payload);
    expect(api.session.addQueriedAddress).toHaveBeenCalledWith(payload);
    expect(store.state.session!.queriedAddresses).toMatchObject({});
    expect(useMainStore().message.description).toBeTruthy();
  });

  test('deletedQueriedAddress', async () => {
    expect.assertions(2);
    const originalState: QueriedAddresses = {
      makerdao_dsr: ['0x52bc44d5378309EE2abF1539BF71dE1b7d7bE3b5']
    };
    store.commit('session/queriedAddresses', originalState);
    const payload: QueriedAddressPayload = {
      module: Module.MAKERDAO_DSR,
      address: '0x52bc44d5378309EE2abF1539BF71dE1b7d7bE3b5'
    };

    api.session.deleteQueriedAddress = vi.fn().mockResolvedValue({});
    await store.dispatch('session/deleteQueriedAddress', payload);
    expect(api.session.deleteQueriedAddress).toHaveBeenCalledWith(payload);
    expect(store.state.session!.queriedAddresses).toMatchObject({});
  });

  test('deletedQueriedAddress failed', async () => {
    expect.assertions(3);
    const originalState: QueriedAddresses = {
      makerdao_dsr: ['0x52bc44d5378309EE2abF1539BF71dE1b7d7bE3b5']
    };
    store.commit('session/queriedAddresses', originalState);
    const payload: QueriedAddressPayload = {
      module: Module.MAKERDAO_DSR,
      address: '0x52bc44d5378309EE2abF1539BF71dE1b7d7bE3b5'
    };

    api.session.deleteQueriedAddress = vi
      .fn()
      .mockRejectedValue(new Error('failed'));
    await store.dispatch('session/deleteQueriedAddress', payload);
    expect(api.session.deleteQueriedAddress).toHaveBeenCalledWith(payload);
    expect(store.state.session!.queriedAddresses).toMatchObject(originalState);
    expect(useMainStore().message.description).toBeTruthy();
  });
});
