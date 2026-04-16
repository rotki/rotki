import { beforeEach, describe, expect, it, vi } from 'vitest';
import { useAddressBookOperations } from '@/modules/accounts/address-book/use-address-book-operations';
import { useAddressNameResolution } from '@/modules/accounts/address-book/use-address-name-resolution';
import { useAddressesNamesApi } from '@/modules/accounts/address-book/use-addresses-names-api';
import { defaultCollectionState } from '@/modules/core/common/data/collection-utils';

vi.mock('@/modules/accounts/address-book/use-addresses-names-api', () => ({
  useAddressesNamesApi: vi.fn().mockReturnValue({
    addAddressBook: vi.fn().mockResolvedValue(true),
    deleteAddressBook: vi.fn().mockResolvedValue(true),
    fetchAddressBook: vi.fn().mockResolvedValue({ data: [], totalCount: 0 }),
    updateAddressBook: vi.fn().mockResolvedValue(true),
  }),
}));

vi.mock('@/modules/accounts/address-book/use-address-name-resolution', () => ({
  useAddressNameResolution: vi.fn().mockReturnValue({
    resetAddressNamesData: vi.fn(),
  }),
}));

vi.mock('@/modules/core/notifications/use-notifications', () => ({
  useNotifications: vi.fn().mockReturnValue({
    notifyError: vi.fn(),
  }),
}));

describe('useAddressBookOperations', () => {
  let api: ReturnType<typeof useAddressesNamesApi>;
  let resolution: ReturnType<typeof useAddressNameResolution>;

  setActivePinia(createPinia());

  beforeEach(() => {
    api = useAddressesNamesApi();
    resolution = useAddressNameResolution();
    vi.clearAllMocks();
  });

  describe('addAddressBook', () => {
    it('should add entries and reset names on success', async () => {
      const entries = [{ address: '0xAddr1', blockchain: 'eth', name: 'Test' }];
      const { addAddressBook } = useAddressBookOperations();

      const result = await addAddressBook('private', entries);

      expect(result).toBe(true);
      expect(api.addAddressBook).toHaveBeenCalledWith('private', entries, false);
      expect(resolution.resetAddressNamesData).toHaveBeenCalledWith(entries);
    });

    it('should not reset names on failure', async () => {
      vi.mocked(api.addAddressBook).mockResolvedValue(false);
      const entries = [{ address: '0xAddr1', blockchain: 'eth', name: 'Test' }];
      const { addAddressBook } = useAddressBookOperations();

      const result = await addAddressBook('private', entries);

      expect(result).toBe(false);
      expect(resolution.resetAddressNamesData).not.toHaveBeenCalled();
    });
  });

  describe('updateAddressBook', () => {
    it('should update entries and reset names on success', async () => {
      const entries = [{ address: '0xAddr1', blockchain: 'eth', name: 'Updated' }];
      const { updateAddressBook } = useAddressBookOperations();

      const result = await updateAddressBook('private', entries);

      expect(result).toBe(true);
      expect(api.updateAddressBook).toHaveBeenCalledWith('private', entries);
      expect(resolution.resetAddressNamesData).toHaveBeenCalledWith(entries);
    });
  });

  describe('deleteAddressBook', () => {
    it('should delete entries and reset names on success', async () => {
      const addresses = [{ address: '0xAddr1', blockchain: 'eth' }];
      const { deleteAddressBook } = useAddressBookOperations();

      const result = await deleteAddressBook('private', addresses);

      expect(result).toBe(true);
      expect(api.deleteAddressBook).toHaveBeenCalledWith('private', addresses);
      expect(resolution.resetAddressNamesData).toHaveBeenCalledWith(addresses);
    });
  });

  describe('getAddressBook', () => {
    it('should fetch address book entries', async () => {
      const mockData = {
        data: [{ address: '0xAddr1', blockchain: 'eth', name: 'Test' }],
        found: 1,
        limit: 10,
        total: 1,
      };
      vi.mocked(api.fetchAddressBook).mockResolvedValue(mockData);

      const { getAddressBook } = useAddressBookOperations();
      const result = await getAddressBook('private', { limit: 10, offset: 0 });

      expect(result).toEqual(mockData);
      expect(api.fetchAddressBook).toHaveBeenCalledWith('private', { limit: 10, offset: 0 });
    });

    it('should return default collection state on error', async () => {
      vi.mocked(api.fetchAddressBook).mockRejectedValue(new Error('Network error'));

      const { getAddressBook } = useAddressBookOperations();
      const result = await getAddressBook('private', { limit: 10, offset: 0 });

      expect(result).toEqual(defaultCollectionState());
    });
  });
});
