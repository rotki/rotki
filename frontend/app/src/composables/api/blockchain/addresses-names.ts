import { type ActionResult } from '@rotki/common/lib/data';
import { snakeCaseTransformer } from '@/services/axios-tranformers';
import { api } from '@/services/rotkehlchen-api';
import {
  handleResponse,
  validWithSessionAndExternalService
} from '@/services/utils';
import {
  AddressBookEntries,
  type AddressBookLocation,
  type AddressBookSimplePayload,
  EthNames
} from '@/types/eth-names';
import { type PendingTask } from '@/types/task';

export const useAddressesNamesApi = () => {
  const internalEnsNames = async <T>(
    ethereumAddresses: string[],
    asyncQuery = false
  ): Promise<T> => {
    const response = await api.instance.post<ActionResult<T>>(
      '/names/ens/reverse',
      snakeCaseTransformer({
        ethereumAddresses,
        asyncQuery,
        ignoreCache: asyncQuery
      }),
      {
        validateStatus: validWithSessionAndExternalService
      }
    );

    return handleResponse(response);
  };

  const getEnsNamesTask = async (
    ethAddresses: string[]
  ): Promise<PendingTask> => {
    return await internalEnsNames<PendingTask>(ethAddresses, true);
  };

  const getEnsNames = async (ethAddresses: string[]): Promise<EthNames> => {
    const response = await internalEnsNames<EthNames>(ethAddresses);

    return EthNames.parse(response);
  };

  const getAddressBook = async (
    location: AddressBookLocation,
    addresses?: string[]
  ): Promise<AddressBookEntries> => {
    const response = await api.instance.post<ActionResult<EthNames>>(
      `/names/addressbook/${location}`,
      addresses ? { addresses } : null,
      {
        validateStatus: validWithSessionAndExternalService
      }
    );

    return AddressBookEntries.parse(handleResponse(response));
  };

  const addAddressBook = async (
    location: AddressBookLocation,
    entries: AddressBookEntries
  ): Promise<boolean> => {
    const response = await api.instance.put<ActionResult<boolean>>(
      `/names/addressbook/${location}`,
      { entries },
      {
        validateStatus: validWithSessionAndExternalService
      }
    );

    return handleResponse(response);
  };

  const updateAddressBook = async (
    location: AddressBookLocation,
    entries: AddressBookEntries
  ): Promise<boolean> => {
    const response = await api.instance.patch<ActionResult<boolean>>(
      `/names/addressbook/${location}`,
      { entries },
      {
        validateStatus: validWithSessionAndExternalService
      }
    );

    return handleResponse(response);
  };

  const deleteAddressBook = async (
    location: AddressBookLocation,
    addresses: AddressBookSimplePayload[]
  ): Promise<boolean> => {
    const response = await api.instance.delete<ActionResult<boolean>>(
      `/names/addressbook/${location}`,
      {
        data: snakeCaseTransformer({ addresses }),
        validateStatus: validWithSessionAndExternalService
      }
    );

    return handleResponse(response);
  };

  const getAddressesNames = async (
    addresses: AddressBookSimplePayload[]
  ): Promise<AddressBookEntries> => {
    const response = await api.instance.post<ActionResult<AddressBookEntries>>(
      '/names',
      { addresses },
      {
        validateStatus: validWithSessionAndExternalService
      }
    );

    return handleResponse(response);
  };

  return {
    getEnsNamesTask,
    getEnsNames,
    getAddressBook,
    addAddressBook,
    updateAddressBook,
    deleteAddressBook,
    getAddressesNames
  };
};
