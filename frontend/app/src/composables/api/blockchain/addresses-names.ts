import { omit } from 'es-toolkit';
import { snakeCaseTransformer } from '@/services/axios-transformers';
import { api } from '@/services/rotkehlchen-api';
import { handleResponse, validStatus, validWithSessionAndExternalService } from '@/services/utils';
import {
  AddressBookCollectionResponse,
  type AddressBookEntries,
  type AddressBookEntry,
  type AddressBookLocation,
  type AddressBookRequestPayload,
  type AddressBookSimplePayload,
  EthNames,
} from '@/types/eth-names';
import { mapCollectionResponse } from '@/utils/collection';
import type { ActionResult } from '@rotki/common';
import type { PendingTask } from '@/types/task';
import type { Collection, CollectionResponse } from '@/types/collection';

interface UseAddressesNamesApiReturn {
  getEnsNamesTask: (ethAddresses: string[]) => Promise<PendingTask>;
  getEnsNames: (ethAddresses: string[]) => Promise<EthNames>;
  fetchAddressBook: (location: AddressBookLocation, payload: AddressBookRequestPayload) => Promise<Collection<AddressBookEntry>>;
  addAddressBook: (location: AddressBookLocation, entries: AddressBookEntries) => Promise<boolean>;
  updateAddressBook: (location: AddressBookLocation, entries: AddressBookEntries) => Promise<boolean>;
  deleteAddressBook: (location: AddressBookLocation, addresses: AddressBookSimplePayload[]) => Promise<boolean>;
  getAddressesNames: (addresses: AddressBookSimplePayload[]) => Promise<AddressBookEntries>;
  ensAvatarUrl: (ens: string, timestamp?: number) => string;
  clearEnsAvatarCache: (listEns: string[] | null) => Promise<boolean>;
}

export function useAddressesNamesApi(): UseAddressesNamesApiReturn {
  const internalEnsNames = async <T>(ethereumAddresses: string[], asyncQuery = false): Promise<T> => {
    const response = await api.instance.post<ActionResult<T>>(
      '/names/ens/reverse',
      snakeCaseTransformer({
        asyncQuery,
        ethereumAddresses,
        ignoreCache: asyncQuery,
      }),
      {
        validateStatus: validWithSessionAndExternalService,
      },
    );

    return handleResponse(response);
  };

  const getEnsNamesTask = async (ethAddresses: string[]): Promise<PendingTask> =>
    internalEnsNames<PendingTask>(ethAddresses, true);

  const getEnsNames = async (ethAddresses: string[]): Promise<EthNames> => {
    const response = await internalEnsNames<EthNames>(ethAddresses);

    return EthNames.parse(response);
  };

  const fetchAddressBook = async (
    location: AddressBookLocation,
    payload: AddressBookRequestPayload,
  ): Promise<Collection<AddressBookEntry>> => {
    const payloadVal = get(payload);
    const filteredPayload = omit(payloadVal, ['address']);
    const response = await api.instance.post<ActionResult<CollectionResponse<AddressBookEntry>>>(
      `/names/addressbook/${location}`,
      snakeCaseTransformer({
        ...filteredPayload,
        addresses: payloadVal.address?.map(address => ({ address })),
      }),
      {
        validateStatus: validWithSessionAndExternalService,
      },
    );

    return mapCollectionResponse(AddressBookCollectionResponse.parse(handleResponse(response)));
  };

  const addAddressBook = async (location: AddressBookLocation, entries: AddressBookEntries): Promise<boolean> => {
    const response = await api.instance.put<ActionResult<boolean>>(
      `/names/addressbook/${location}`,
      { entries },
      {
        validateStatus: validWithSessionAndExternalService,
      },
    );

    return handleResponse(response);
  };

  const updateAddressBook = async (location: AddressBookLocation, entries: AddressBookEntries): Promise<boolean> => {
    const response = await api.instance.patch<ActionResult<boolean>>(
      `/names/addressbook/${location}`,
      { entries },
      {
        validateStatus: validWithSessionAndExternalService,
      },
    );

    return handleResponse(response);
  };

  const deleteAddressBook = async (
    location: AddressBookLocation,
    addresses: AddressBookSimplePayload[],
  ): Promise<boolean> => {
    const response = await api.instance.delete<ActionResult<boolean>>(`/names/addressbook/${location}`, {
      data: snakeCaseTransformer({ addresses }),
      validateStatus: validWithSessionAndExternalService,
    });

    return handleResponse(response);
  };

  const getAddressesNames = async (addresses: AddressBookSimplePayload[]): Promise<AddressBookEntries> => {
    const response = await api.instance.post<ActionResult<AddressBookEntries>>(
      '/names',
      { addresses },
      {
        validateStatus: validWithSessionAndExternalService,
      },
    );

    return handleResponse(response);
  };

  const ensAvatarUrl = (ens: string, timestamp?: number): string => {
    let url = `${api.instance.defaults.baseURL}avatars/ens/${ens}`;

    if (timestamp)
      url += `?timestamp=${timestamp}`;

    return url;
  };

  const clearEnsAvatarCache = async (listEns: string[] | null): Promise<boolean> => {
    const response = await api.instance.post<ActionResult<boolean>>(
      '/cache/avatars/clear',
      { entries: listEns },
      {
        validateStatus: validStatus,
      },
    );

    return handleResponse(response);
  };

  return {
    addAddressBook,
    clearEnsAvatarCache,
    deleteAddressBook,
    ensAvatarUrl,
    fetchAddressBook,
    getAddressesNames,
    getEnsNames,
    getEnsNamesTask,
    updateAddressBook,
  };
}
