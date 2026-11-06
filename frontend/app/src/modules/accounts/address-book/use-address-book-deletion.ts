import type { MaybeRef } from 'vue';
import type { AddressBookEntry, AddressBookLocation } from '@/modules/accounts/address-book/eth-names';
import { useAddressBookOperations } from '@/modules/accounts/address-book/use-address-book-operations';
import { getErrorMessage } from '@/modules/core/common/logging/error-handling';
import { useNotifications } from '@/modules/core/notifications/use-notifications';

interface UseAddressBookDeletionReturn {
  deleteAddressBook: (address: string, blockchain: string | null) => Promise<void>;
  /** What the entry's delete button asks, beside it, before `deleteEntry` runs. */
  deleteConfirm: (item: AddressBookEntry) => { title: string; message: string };
  /** Deletes an entry the user already confirmed. */
  deleteEntry: (item: AddressBookEntry) => Promise<void>;
}

export function useAddressBookDeletion(
  location: MaybeRef<AddressBookLocation>,
  onSuccess?: () => void,
): UseAddressBookDeletionReturn {
  const { t } = useI18n({ useScope: 'global' });
  const { notifyError } = useNotifications();
  const { deleteAddressBook: deleteAddressBookCaller } = useAddressBookOperations();

  const deleteAddressBook = async (address: string, blockchain: string | null): Promise<void> => {
    try {
      await deleteAddressBookCaller(get(location), [{ address, blockchain }]);
      onSuccess?.();
    }
    catch (error: unknown) {
      notifyError(
        t('address_book.actions.delete.error.title'),
        t('address_book.actions.delete.error.description', {
          address,
          chain: blockchain ?? t('common.multi_chain'),
          message: getErrorMessage(error),
        }),
      );
    }
  };

  const deleteConfirm = (item: AddressBookEntry): { title: string; message: string } => ({
    message: t('address_book.actions.delete.dialog.message', {
      address: item.address,
      chain: item.blockchain ?? t('common.multi_chain'),
    }),
    title: t('address_book.actions.delete.dialog.title'),
  });

  const deleteEntry = async (item: AddressBookEntry): Promise<void> => deleteAddressBook(item.address, item.blockchain);

  return {
    deleteAddressBook,
    deleteConfirm,
    deleteEntry,
  };
}
