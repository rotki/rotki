import type { MaybeRef } from '@vueuse/core';
import type { AddressBookEntry, AddressBookLocation } from '@/types/eth-names';
import { NotificationCategory, Severity } from '@rotki/common';
import { useAddressesNamesStore } from '@/store/blockchain/accounts/addresses-names';
import { useConfirmStore } from '@/store/confirm';
import { useNotificationsStore } from '@/store/notifications';

interface UseAddressBookDeletionReturn {
  deleteAddressBook: (address: string, blockchain: string | null) => Promise<void>;
  showDeleteConfirmation: (item: AddressBookEntry) => void;
}

export function useAddressBookDeletion(
  location: MaybeRef<AddressBookLocation>,
  onSuccess?: () => void,
): UseAddressBookDeletionReturn {
  const { t } = useI18n();
  const { show } = useConfirmStore();
  const { notify } = useNotificationsStore();
  const { deleteAddressBook: deleteAddressBookCaller } = useAddressesNamesStore();

  const deleteAddressBook = async (address: string, blockchain: string | null): Promise<void> => {
    try {
      await deleteAddressBookCaller(get(location), [{ address, blockchain }]);
      onSuccess?.();
    }
    catch (error: any) {
      notify({
        category: NotificationCategory.DEFAULT,
        display: true,
        message: t('address_book.actions.delete.error.description', {
          address,
          chain: blockchain || t('common.multi_chain'),
          message: error.message,
        }),
        severity: Severity.ERROR,
        title: t('address_book.actions.delete.error.title'),
      });
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
