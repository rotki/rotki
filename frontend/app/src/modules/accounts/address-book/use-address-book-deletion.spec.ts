import type { AddressBookEntry } from '@/modules/accounts/address-book/eth-names';
import { createMock } from '@test/utils/create-mock';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { useAddressBookDeletion } from './use-address-book-deletion';

const { spies } = vi.hoisted(() => ({
  spies: {
    show: vi.fn(),
    notifyError: vi.fn(),
    deleteAddressBook: vi.fn(),
  },
}));

vi.mock('@/modules/core/common/use-confirm-store', () => ({
  useConfirmStore: (): object => ({ show: spies.show }),
}));
vi.mock('@/modules/core/notifications/use-notifications', () => ({
  useNotifications: (): object => ({ notifyError: spies.notifyError }),
}));
vi.mock('@/modules/accounts/address-book/use-address-book-operations', () => ({
  useAddressBookOperations: (): object => ({ deleteAddressBook: spies.deleteAddressBook }),
}));

describe('useAddressBookDeletion', () => {
  beforeEach(() => {
    spies.deleteAddressBook.mockResolvedValue(undefined);
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  it('should delete an entry and call the success callback', async () => {
    const onSuccess = vi.fn();
    const { deleteAddressBook } = useAddressBookDeletion('private', onSuccess);
    await deleteAddressBook('0xabc', 'eth');
    expect(spies.deleteAddressBook).toHaveBeenCalledWith('private', [{ address: '0xabc', blockchain: 'eth' }]);
    expect(onSuccess).toHaveBeenCalledOnce();
  });

  it('should notify and skip the callback when deletion fails', async () => {
    spies.deleteAddressBook.mockRejectedValue(new Error('boom'));
    const onSuccess = vi.fn();
    const { deleteAddressBook } = useAddressBookDeletion('global', onSuccess);
    await deleteAddressBook('0xabc', null);
    expect(spies.notifyError).toHaveBeenCalledOnce();
    expect(onSuccess).not.toHaveBeenCalled();
  });

  it('should delete through the confirmation dialog', async () => {
    const { showDeleteConfirmation } = useAddressBookDeletion('private');
    showDeleteConfirmation(createMock<AddressBookEntry>({ address: '0xdef', blockchain: 'optimism' }));
    expect(spies.show).toHaveBeenCalledOnce();
    await spies.show.mock.calls[0][1]();
    expect(spies.deleteAddressBook).toHaveBeenCalledWith('private', [{ address: '0xdef', blockchain: 'optimism' }]);
  });
});
