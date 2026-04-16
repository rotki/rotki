import type {
  AddressBookEntries,
  AddressBookEntry,
  AddressBookLocation,
  AddressBookRequestPayload,
  AddressBookSimplePayload,
} from '@/modules/address-names/eth-names';
import type { Collection } from '@/modules/common/collection';
import { useAddressesNamesApi } from '@/composables/api/blockchain/addresses-names';
import { useAddressNameResolution } from '@/modules/address-names/use-address-name-resolution';
import { defaultCollectionState } from '@/modules/common/data/collection-utils';
import { getErrorMessage } from '@/modules/common/logging/error-handling';
import { logger } from '@/modules/common/logging/logging';
import { useNotifications } from '@/modules/notifications/use-notifications';

interface UseAddressBookOperationsReturn {
  addAddressBook: (location: AddressBookLocation, entries: AddressBookEntries, updateExisting?: boolean) => Promise<boolean>;
  deleteAddressBook: (location: AddressBookLocation, addresses: AddressBookSimplePayload[]) => Promise<boolean>;
  getAddressBook: (location: AddressBookLocation, payload: AddressBookRequestPayload) => Promise<Collection<AddressBookEntry>>;
  updateAddressBook: (location: AddressBookLocation, entries: AddressBookEntries) => Promise<boolean>;
}

export function useAddressBookOperations(): UseAddressBookOperationsReturn {
  const { notifyError } = useNotifications();
  const { t } = useI18n({ useScope: 'global' });
  const { resetAddressNamesData } = useAddressNameResolution();

  const {
    addAddressBook: addAddressBookCaller,
    deleteAddressBook: deleteAddressBookCaller,
    fetchAddressBook,
    updateAddressBook: updateAddressBookCaller,
  } = useAddressesNamesApi();

  const getAddressBook = async (
    location: AddressBookLocation,
    payload: AddressBookRequestPayload,
  ): Promise<Collection<AddressBookEntry>> => {
    try {
      return await fetchAddressBook(location, payload);
    }
    catch (error: unknown) {
      logger.error(error);
      notifyError(
        t('address_book.actions.fetch.error.title'),
        t('address_book.actions.fetch.error.message', {
          message: getErrorMessage(error),
        }),
      );

      return defaultCollectionState();
    }
  };

  const addAddressBook = async (
    location: AddressBookLocation,
    entries: AddressBookEntries,
    updateExisting = false,
  ): Promise<boolean> => {
    const result = await addAddressBookCaller(location, entries, updateExisting);

    if (result)
      resetAddressNamesData(entries);

    return result;
  };

  const updateAddressBook = async (
    location: AddressBookLocation,
    entries: AddressBookEntries,
  ): Promise<boolean> => {
    const result = await updateAddressBookCaller(location, entries);

    if (result)
      resetAddressNamesData(entries);

    return result;
  };

  const deleteAddressBook = async (
    location: AddressBookLocation,
    addresses: AddressBookSimplePayload[],
  ): Promise<boolean> => {
    const result = await deleteAddressBookCaller(location, addresses);

    if (result)
      resetAddressNamesData(addresses);

    return result;
  };

  return {
    addAddressBook,
    deleteAddressBook,
    getAddressBook,
    updateAddressBook,
  };
}
