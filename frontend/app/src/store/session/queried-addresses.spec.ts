import type { QueriedAddresses, QueriedAddressPayload } from '@/types/session';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { useQueriedAddressApi } from '@/composables/api/session/queried-addresses';
import { useMessageStore } from '@/store/message';
import { useQueriedAddressesStore } from '@/store/session/queried-addresses';
import { Module } from '@/types/modules';

describe('useQueriedAddressesStore', () => {
  setActivePinia(createPinia());
  let store: ReturnType<typeof useQueriedAddressesStore>;
  let api: ReturnType<typeof useQueriedAddressApi>;

  beforeEach(() => {
    store = useQueriedAddressesStore();
    api = useQueriedAddressApi();
  });

  it('should fetch queried addresses', async () => {
    expect.assertions(2);

    const response: QueriedAddresses = {
      makerdaoDsr: ['0x52bc44d5378309EE2abF1539BF71dE1b7d7bE3b5'],
    };

    api.queriedAddresses = vi.fn().mockResolvedValue(response);
    await store.fetchQueriedAddresses();
    expect(api.queriedAddresses).toHaveBeenCalledTimes(1);
    expect(store.queriedAddresses).toMatchObject(response);
  });

  it('should handle fetchQueriedAddresses failure', async () => {
    expect.assertions(3);
    const messageStore = useMessageStore();
    api.queriedAddresses = vi.fn().mockRejectedValue(new Error('failed'));
    await store.fetchQueriedAddresses();
    expect(api.queriedAddresses).toHaveBeenCalledTimes(1);
    expect(store.queriedAddresses).toMatchObject({});
    expect(messageStore.message?.description).toBeTruthy();
  });

  it('should add queried address', async () => {
    expect.assertions(2);
    const payload: QueriedAddressPayload = {
      module: Module.MAKERDAO_DSR,
      address: '0x52bc44d5378309EE2abF1539BF71dE1b7d7bE3b5',
    };
    const response: QueriedAddresses = {
      makerdaoDsr: ['0x52bc44d5378309EE2abF1539BF71dE1b7d7bE3b5'],
    };
    api.addQueriedAddress = vi.fn().mockResolvedValue(response);
    await store.addQueriedAddress(payload);
    expect(api.addQueriedAddress).toHaveBeenCalledWith(payload);
    expect(store.queriedAddresses).toMatchObject(response);
  });

  it('should handle addQueriedAddress failure', async () => {
    expect.assertions(3);
    const messageStore = useMessageStore();
    const payload: QueriedAddressPayload = {
      module: Module.MAKERDAO_DSR,
      address: '0x52bc44d5378309EE2abF1539BF71dE1b7d7bE3b5',
    };

    api.addQueriedAddress = vi.fn().mockRejectedValue(new Error('failed'));
    await store.addQueriedAddress(payload);
    expect(api.addQueriedAddress).toHaveBeenCalledWith(payload);
    expect(store.queriedAddresses).toMatchObject({});
    expect(messageStore.message?.description).toBeTruthy();
  });

  it('should delete queried address', async () => {
    expect.assertions(2);

    const originalState: QueriedAddresses = {
      makerdaoDsr: ['0x52bc44d5378309EE2abF1539BF71dE1b7d7bE3b5'],
    };
    Object.assign(store.queriedAddresses, originalState);
    const payload: QueriedAddressPayload = {
      module: Module.MAKERDAO_DSR,
      address: '0x52bc44d5378309EE2abF1539BF71dE1b7d7bE3b5',
    };

    api.deleteQueriedAddress = vi.fn().mockResolvedValue({});
    await store.deleteQueriedAddress(payload);
    expect(api.deleteQueriedAddress).toHaveBeenCalledWith(payload);
    expect(store.queriedAddresses).toMatchObject({});
  });

  it('should handle deleteQueriedAddress failure', async () => {
    expect.assertions(3);
    const messageStore = useMessageStore();

    const originalState: QueriedAddresses = {
      makerdaoDsr: ['0x52bc44d5378309EE2abF1539BF71dE1b7d7bE3b5'],
    };
    Object.assign(store.queriedAddresses, originalState);
    const payload: QueriedAddressPayload = {
      module: Module.MAKERDAO_DSR,
      address: '0x52bc44d5378309EE2abF1539BF71dE1b7d7bE3b5',
    };

    api.deleteQueriedAddress = vi.fn().mockRejectedValue(new Error('failed'));
    await store.deleteQueriedAddress(payload);
    expect(api.deleteQueriedAddress).toHaveBeenCalledWith(payload);
    expect(store.queriedAddresses).toMatchObject(originalState);
    expect(messageStore.message?.description).toBeTruthy();
  });
});
