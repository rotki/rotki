import type { QueriedAddresses, QueriedAddressPayload } from '@/modules/session/types';
import { createPinia, setActivePinia } from 'pinia';
import { err, ok } from 'plainfp/result';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { Module } from '@/modules/core/common/modules';
import { useSessionMetadataStore } from '@/modules/session/use-session-metadata-store';
import '@test/i18n';

const mockQueriedAddresses = vi.fn();
const mockAddQueriedAddress = vi.fn();
const mockDeleteQueriedAddress = vi.fn();
const mockNotifyError = vi.fn<(title: string, message: string) => void>();

vi.mock('@/modules/accounts/api/use-queried-address-api', () => ({
  useQueriedAddressApi: vi.fn(() => ({
    addQueriedAddress: mockAddQueriedAddress,
    deleteQueriedAddress: mockDeleteQueriedAddress,
    queriedAddresses: mockQueriedAddresses,
  })),
}));

vi.mock('@/modules/core/notifications/use-notifications', () => ({
  getErrorMessage: vi.fn((e: unknown): string => (e instanceof Error ? e.message : String(e))),
  useNotifications: vi.fn(() => ({
    notifyError: mockNotifyError,
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

    it('should pop a notification on fetch failure, which has no dialog to show it', async () => {
      mockQueriedAddresses.mockRejectedValue(new Error('failed'));

      const { useQueriedAddressOperations } = await importModule();
      const { fetchQueriedAddresses } = useQueriedAddressOperations();
      await fetchQueriedAddresses();

      const store = useSessionMetadataStore();
      expect(mockQueriedAddresses).toHaveBeenCalledOnce();
      expect(get(store.queriedAddresses)).toStrictEqual({});
      expect(mockNotifyError).toHaveBeenCalledWith(
        'queried_address_dialog.title',
        'actions.session.fetch_queriable_address.error.message::failed',
      );
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
      const failure = await addQueriedAddress(payload);

      const store = useSessionMetadataStore();
      expect(mockAddQueriedAddress).toHaveBeenCalledWith(payload);
      expect(get(store.queriedAddresses)).toMatchObject(response);
      expect(failure).toStrictEqual(ok(undefined));
    });

    it('should hand an add failure back instead of showing it', async () => {
      const payload: QueriedAddressPayload = {
        address: '0x52bc44d5378309EE2abF1539BF71dE1b7d7bE3b5',
        module: Module.MAKERDAO_DSR,
      };
      const error = new Error('failed');
      mockAddQueriedAddress.mockRejectedValue(error);

      const { useQueriedAddressOperations } = await importModule();
      const { addQueriedAddress } = useQueriedAddressOperations();
      const failure = await addQueriedAddress(payload);

      const store = useSessionMetadataStore();
      expect(mockAddQueriedAddress).toHaveBeenCalledWith(payload);
      expect(get(store.queriedAddresses)).toStrictEqual({});
      expect(failure).toStrictEqual(err(error));
      expect(mockNotifyError).not.toHaveBeenCalled();
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
      const failure = await deleteQueriedAddress(payload);

      expect(mockDeleteQueriedAddress).toHaveBeenCalledWith(payload);
      expect(get(queriedAddresses)).toStrictEqual({});
      expect(failure).toStrictEqual(ok(undefined));
    });

    it('should hand a delete failure back instead of showing it', async () => {
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
      const error = new Error('failed');
      mockDeleteQueriedAddress.mockRejectedValue(error);

      const { useQueriedAddressOperations } = await importModule();
      const { deleteQueriedAddress } = useQueriedAddressOperations();
      const failure = await deleteQueriedAddress(payload);

      expect(mockDeleteQueriedAddress).toHaveBeenCalledWith(payload);
      expect(get(queriedAddresses)).toMatchObject(originalState);
      expect(failure).toStrictEqual(err(error));
      expect(mockNotifyError).not.toHaveBeenCalled();
    });
  });
});
