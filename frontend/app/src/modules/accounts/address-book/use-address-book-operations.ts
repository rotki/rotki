import type { ResultAsync } from 'plainfp/result-async';
import type {
  AddressBookEntries,
  AddressBookEntry,
  AddressBookLocation,
  AddressBookRequestPayload,
  AddressBookSimplePayload,
} from '@/modules/accounts/address-book/eth-names';
import type { Collection } from '@/modules/core/common/collection';
import { useAddressNameResolution } from '@/modules/accounts/address-book/use-address-name-resolution';
import { useAddressesNamesApi } from '@/modules/accounts/address-book/use-addresses-names-api';
import { fromRequest, type RequestError } from '@/modules/core/api/request-result';

interface UseAddressBookOperationsReturn {
  addAddressBook: (location: AddressBookLocation, entries: AddressBookEntries, updateExisting?: boolean) => Promise<boolean>;
  deleteAddressBook: (location: AddressBookLocation, addresses: AddressBookSimplePayload[]) => Promise<boolean>;
  getAddressBook: (location: AddressBookLocation, payload: AddressBookRequestPayload) => ResultAsync<Collection<AddressBookEntry>, RequestError>;
  updateAddressBook: (location: AddressBookLocation, entries: AddressBookEntries) => Promise<boolean>;
}

export function useAddressBookOperations(): UseAddressBookOperationsReturn {
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
  ): ResultAsync<Collection<AddressBookEntry>, RequestError> =>
    fromRequest(async () => fetchAddressBook(location, payload));

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
