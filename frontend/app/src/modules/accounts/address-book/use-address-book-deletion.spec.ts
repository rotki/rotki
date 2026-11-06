import type { AddressBookEntry } from '@/modules/accounts/address-book/eth-names';
import { createMock } from '@test/utils/create-mock';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { useAddressBookDeletion } from './use-address-book-deletion';

const { spies } = vi.hoisted(() => ({
  spies: {
    notifyError: vi.fn(),
    deleteAddressBook: vi.fn(),
  },
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

  it('should delete the confirmed entry from its chain', async () => {
    const { deleteEntry } = useAddressBookDeletion('private');
    await deleteEntry(createMock<AddressBookEntry>({ address: '0xdef', blockchain: 'optimism' }));
    expect(spies.deleteAddressBook).toHaveBeenCalledWith('private', [{ address: '0xdef', blockchain: 'optimism' }]);
  });

  it('should ask about the entry by its address and chain', () => {
    const { deleteConfirm } = useAddressBookDeletion('private');
    expect(deleteConfirm(createMock<AddressBookEntry>({ address: '0xdef', blockchain: 'optimism' }))).toEqual({
      message: 'address_book.actions.delete.dialog.message::0xdef, optimism',
      title: 'address_book.actions.delete.dialog.title',
    });
  });

  it('should ask about an entry for every chain as multi-chain', () => {
    const { deleteConfirm } = useAddressBookDeletion('global');
    expect(deleteConfirm(createMock<AddressBookEntry>({ address: '0xdef', blockchain: null })).message)
      .toBe('address_book.actions.delete.dialog.message::0xdef, common.multi_chain');
  });
});
