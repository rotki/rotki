import type { QueriedAddresses, QueriedAddressPayload } from '@/modules/session/types';
import { createPinia, setActivePinia } from 'pinia';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { Module } from '@/modules/common/modules';
import { useSessionMetadataStore } from '@/store/session/metadata';
import '@test/i18n';

const mockQueriedAddresses = vi.fn();
const mockAddQueriedAddress = vi.fn();
const mockDeleteQueriedAddress = vi.fn();
const mockShowErrorMessage = vi.fn();

vi.mock('@/composables/api/session/queried-addresses', () => ({
  useQueriedAddressApi: vi.fn(() => ({
    addQueriedAddress: mockAddQueriedAddress,
    deleteQueriedAddress: mockDeleteQueriedAddress,
    queriedAddresses: mockQueriedAddresses,
  })),
}));

vi.mock('@/modules/notifications/use-notifications', () => ({
  getErrorMessage: vi.fn((e: unknown): string => (e instanceof Error ? e.message : String(e))),
  useNotifications: vi.fn(() => ({
    showErrorMessage: mockShowErrorMessage,
  })),
}));

describe('useQueriedAddressOperations', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  async function importModule(): Promise<typeof import('./use-queried-address-operations')> {
    return import('./use-queried-address-operations');
  }

  describe('fetchQueriedAddresses', () => {
    it('should populate store with fetched queried addresses', async () => {
      const response: QueriedAddresses = {
        makerdaoDsr: ['0x52bc44d5378309EE2abF1539BF71dE1b7d7bE3b5'],
      };
      mockQueriedAddresses.mockResolvedValue(response);

      const { useQueriedAddressOperations } = await importModule();
      const { fetchQueriedAddresses } = useQueriedAddressOperations();
      await fetchQueriedAddresses();

      const store = useSessionMetadataStore();
      expect(mockQueriedAddresses).toHaveBeenCalledOnce();
      expect(get(store.queriedAddresses)).toMatchObject(response);
    });

    it('should show error on fetch failure', async () => {
      mockQueriedAddresses.mockRejectedValue(new Error('failed'));

      const { useQueriedAddressOperations } = await importModule();
      const { fetchQueriedAddresses } = useQueriedAddressOperations();
      await fetchQueriedAddresses();

      const store = useSessionMetadataStore();
      expect(mockQueriedAddresses).toHaveBeenCalledOnce();
      expect(get(store.queriedAddresses)).toMatchObject({});
      expect(mockShowErrorMessage).toHaveBeenCalledOnce();
    });
  });

  describe('addQueriedAddress', () => {
    it('should add queried address and update store', async () => {
      const payload: QueriedAddressPayload = {
        address: '0x52bc44d5378309EE2abF1539BF71dE1b7d7bE3b5',
        module: Module.MAKERDAO_DSR,
      };
      const response: QueriedAddresses = {
        makerdaoDsr: ['0x52bc44d5378309EE2abF1539BF71dE1b7d7bE3b5'],
      };
      mockAddQueriedAddress.mockResolvedValue(response);

      const { useQueriedAddressOperations } = await importModule();
      const { addQueriedAddress } = useQueriedAddressOperations();
      await addQueriedAddress(payload);

      const store = useSessionMetadataStore();
      expect(mockAddQueriedAddress).toHaveBeenCalledWith(payload);
      expect(get(store.queriedAddresses)).toMatchObject(response);
    });

    it('should show error on add failure', async () => {
      const payload: QueriedAddressPayload = {
        address: '0x52bc44d5378309EE2abF1539BF71dE1b7d7bE3b5',
        module: Module.MAKERDAO_DSR,
      };
      mockAddQueriedAddress.mockRejectedValue(new Error('failed'));

      const { useQueriedAddressOperations } = await importModule();
      const { addQueriedAddress } = useQueriedAddressOperations();
      await addQueriedAddress(payload);

      const store = useSessionMetadataStore();
      expect(mockAddQueriedAddress).toHaveBeenCalledWith(payload);
      expect(get(store.queriedAddresses)).toMatchObject({});
      expect(mockShowErrorMessage).toHaveBeenCalledOnce();
    });
  });

  describe('deleteQueriedAddress', () => {
    it('should delete queried address and update store', async () => {
      const store = useSessionMetadataStore();
      const { queriedAddresses } = storeToRefs(store);
      set(queriedAddresses, {
        makerdaoDsr: ['0x52bc44d5378309EE2abF1539BF71dE1b7d7bE3b5'],
      });

      const payload: QueriedAddressPayload = {
        address: '0x52bc44d5378309EE2abF1539BF71dE1b7d7bE3b5',
        module: Module.MAKERDAO_DSR,
      };
      mockDeleteQueriedAddress.mockResolvedValue({});

      const { useQueriedAddressOperations } = await importModule();
      const { deleteQueriedAddress } = useQueriedAddressOperations();
      await deleteQueriedAddress(payload);

      expect(mockDeleteQueriedAddress).toHaveBeenCalledWith(payload);
      expect(get(queriedAddresses)).toMatchObject({});
    });

    it('should show error on delete failure', async () => {
      const store = useSessionMetadataStore();
      const { queriedAddresses } = storeToRefs(store);
      const originalState: QueriedAddresses = {
        makerdaoDsr: ['0x52bc44d5378309EE2abF1539BF71dE1b7d7bE3b5'],
      };
      set(queriedAddresses, originalState);

      const payload: QueriedAddressPayload = {
        address: '0x52bc44d5378309EE2abF1539BF71dE1b7d7bE3b5',
        module: Module.MAKERDAO_DSR,
      };
      mockDeleteQueriedAddress.mockRejectedValue(new Error('failed'));

      const { useQueriedAddressOperations } = await importModule();
      const { deleteQueriedAddress } = useQueriedAddressOperations();
      await deleteQueriedAddress(payload);

      expect(mockDeleteQueriedAddress).toHaveBeenCalledWith(payload);
      expect(get(queriedAddresses)).toMatchObject(originalState);
      expect(mockShowErrorMessage).toHaveBeenCalledOnce();
    });
  });
});
