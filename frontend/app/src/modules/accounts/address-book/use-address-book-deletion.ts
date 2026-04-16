import type { MaybeRef } from 'vue';
import type { AddressBookEntry, AddressBookLocation } from '@/modules/accounts/address-book/eth-names';
import { useAddressBookOperations } from '@/modules/accounts/address-book/use-address-book-operations';
import { getErrorMessage } from '@/modules/core/common/logging/error-handling';
import { useConfirmStore } from '@/modules/core/common/use-confirm-store';
import { useNotifications } from '@/modules/core/notifications/use-notifications';

interface UseAddressBookDeletionReturn {
  deleteAddressBook: (address: string, blockchain: string | null) => Promise<void>;
  showDeleteConfirmation: (item: AddressBookEntry) => void;
}

export function useAddressBookDeletion(
  location: MaybeRef<AddressBookLocation>,
  onSuccess?: () => void,
): UseAddressBookDeletionReturn {
  const { t } = useI18n({ useScope: 'global' });
  const { show } = useConfirmStore();
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
          chain: blockchain || t('common.multi_chain'),
          message: getErrorMessage(error),
        }),
      );
    }
  };

  const showDeleteConfirmation = (item: AddressBookEntry): void => {
    show(
      {
        message: t('address_book.actions.delete.dialog.message', {
          address: item.address,
          chain: item.blockchain || t('common.multi_chain'),
        }),
        title: t('address_book.actions.delete.dialog.title'),
      },
      async () => deleteAddressBook(item.address, item.blockchain),
    );
  };

  return {
    deleteAddressBook,
    showDeleteConfirmation,
  };
}
