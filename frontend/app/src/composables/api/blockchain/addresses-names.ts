import type { Collection, CollectionResponse } from '@/types/collection';
import { omit } from 'es-toolkit';
import { api } from '@/modules/api/rotki-api';
import { VALID_TASK_STATUS, VALID_WITH_SESSION_AND_EXTERNAL_SERVICE } from '@/modules/api/utils';
import {
  AddressBookCollectionResponse,
  type AddressBookEntries,
  AddressBookEntriesSchema,
  type AddressBookEntry,
  type AddressBookLocation,
  type AddressBookRequestPayload,
  type AddressBookSimplePayload,
  type EthNames,
  EthNamesSchema,
} from '@/types/eth-names';
import { type PendingTask, PendingTaskSchema } from '@/types/task';
import { mapCollectionResponse } from '@/utils/collection';

interface UseAddressesNamesApiReturn {
  getEnsNamesTask: (ethAddresses: string[]) => Promise<PendingTask>;
  getEnsNames: (ethAddresses: string[]) => Promise<EthNames>;
  fetchAddressBook: (location: AddressBookLocation, payload: AddressBookRequestPayload) => Promise<Collection<AddressBookEntry>>;
  addAddressBook: (location: AddressBookLocation, entries: AddressBookEntries, updateExisting?: boolean) => Promise<boolean>;
  updateAddressBook: (location: AddressBookLocation, entries: AddressBookEntries) => Promise<boolean>;
  deleteAddressBook: (location: AddressBookLocation, addresses: AddressBookSimplePayload[]) => Promise<boolean>;
  getAddressesNames: (addresses: AddressBookSimplePayload[]) => Promise<AddressBookEntries>;
  ensAvatarUrl: (ens: string, timestamp?: number) => string;
  clearEnsAvatarCache: (listEns: string[] | null) => Promise<boolean>;
  resolveEnsNames: (name: string) => Promise<string>;
}

export function useAddressesNamesApi(): UseAddressesNamesApiReturn {
  const internalEnsNames = async <T>(ethereumAddresses: string[], asyncQuery = false): Promise<T> => api.post<T>(
    '/names/ens/reverse',
    {
      asyncQuery,
      ethereumAddresses,
      ignoreCache: asyncQuery,
    },
    {
      validStatuses: VALID_WITH_SESSION_AND_EXTERNAL_SERVICE,
    },
  );

  const getEnsNamesTask = async (ethAddresses: string[]): Promise<PendingTask> => {
    const response = await internalEnsNames<PendingTask>(ethAddresses, true);
    return PendingTaskSchema.parse(response);
  };

  const getEnsNames = async (ethAddresses: string[]): Promise<EthNames> => {
    const response = await internalEnsNames<EthNames>(ethAddresses);
    return EthNamesSchema.parse(response);
  };

  const resolveEnsNames = async (name: string): Promise<string> => api.post<string>(
    `/names/ens/resolve`,
    { name },
    {
      validStatuses: VALID_TASK_STATUS,
      defaultValue: '',
    },
  );

  const fetchAddressBook = async (
    location: AddressBookLocation,
    payload: AddressBookRequestPayload,
  ): Promise<Collection<AddressBookEntry>> => {
    const payloadVal = get(payload);
    const filteredPayload = omit(payloadVal, ['address']);
    const response = await api.post<CollectionResponse<AddressBookEntry>>(
      `/names/addressbook/${location}`,
      {
        ...filteredPayload,
        addresses: payloadVal.address?.map(address => ({ address })),
      },
      {
        validStatuses: VALID_WITH_SESSION_AND_EXTERNAL_SERVICE,
      },
    );

    return mapCollectionResponse(AddressBookCollectionResponse.parse(response));
  };

  const addAddressBook = async (location: AddressBookLocation, entries: AddressBookEntries, updateExisting = false): Promise<boolean> => api.put<boolean>(
    `/names/addressbook/${location}`,
    {
      entries,
      updateExisting,
    },
    {
      validStatuses: VALID_WITH_SESSION_AND_EXTERNAL_SERVICE,
    },
  );

  const updateAddressBook = async (location: AddressBookLocation, entries: AddressBookEntries): Promise<boolean> => api.patch<boolean>(
    `/names/addressbook/${location}`,
    { entries },
    {
      validStatuses: VALID_WITH_SESSION_AND_EXTERNAL_SERVICE,
    },
  );

  const deleteAddressBook = async (
    location: AddressBookLocation,
    addresses: AddressBookSimplePayload[],
  ): Promise<boolean> => api.delete<boolean>(`/names/addressbook/${location}`, {
    body: { addresses },
    validStatuses: VALID_WITH_SESSION_AND_EXTERNAL_SERVICE,
  });

  const getAddressesNames = async (addresses: AddressBookSimplePayload[]): Promise<AddressBookEntries> => {
    const response = await api.post<AddressBookEntries>(
      '/names',
      { addresses },
      {
        validStatuses: VALID_WITH_SESSION_AND_EXTERNAL_SERVICE,
      },
    );
    return AddressBookEntriesSchema.parse(response);
  };

  const ensAvatarUrl = (ens: string, timestamp?: number): string =>
    api.buildUrl(`avatars/ens/${ens}`, timestamp ? { timestamp } : undefined);

  const clearEnsAvatarCache = async (listEns: string[] | null): Promise<boolean> => api.post<boolean>(
    '/cache/avatars/clear',
    { entries: listEns },
  );

  return {
    addAddressBook,
    clearEnsAvatarCache,
    deleteAddressBook,
    ensAvatarUrl,
    fetchAddressBook,
    getAddressesNames,
    getEnsNames,
    getEnsNamesTask,
    resolveEnsNames,
    updateAddressBook,
  };
}
