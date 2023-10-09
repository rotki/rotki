import { type ActionResult } from '@rotki/common/lib/data';
import { omit } from 'lodash-es';
import { snakeCaseTransformer } from '@/services/axios-tranformers';
import { api } from '@/services/rotkehlchen-api';
import {
  handleResponse,
  validStatus,
  validWithSessionAndExternalService
} from '@/services/utils';
import {
  AddressBookCollectionResponse,
  type AddressBookEntries,
  type AddressBookEntry,
  type AddressBookLocation,
  type AddressBookRequestPayload,
  type AddressBookSimplePayload,
  EthNames
} from '@/types/eth-names';
import { type PendingTask } from '@/types/task';
import { type Collection, type CollectionResponse } from '@/types/collection';

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
  ): Promise<PendingTask> =>
    await internalEnsNames<PendingTask>(ethAddresses, true);

  const getEnsNames = async (ethAddresses: string[]): Promise<EthNames> => {
    const response = await internalEnsNames<EthNames>(ethAddresses);

    return EthNames.parse(response);
  };

  const fetchAddressBook = async (
    location: AddressBookLocation,
    payload: AddressBookRequestPayload
  ): Promise<Collection<AddressBookEntry>> => {
    const payloadVal = get(payload);
    const filteredPayload = omit(payloadVal, [
      'orderByAttributes',
      'ascending',
      'address'
    ]);
    const response = await api.instance.post<
      ActionResult<CollectionResponse<AddressBookEntry>>
    >(
      `/names/addressbook/${location}`,
      snakeCaseTransformer({
        ...filteredPayload,
        addresses: payloadVal.address?.map(address => ({ address }))
      }),
      {
        validateStatus: validWithSessionAndExternalService
      }
    );

    return mapCollectionResponse(
      AddressBookCollectionResponse.parse(handleResponse(response))
    );
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

  const ensAvatarUrl = (ens: string, timestamp?: number): string => {
    let url = `${api.instance.defaults.baseURL}avatars/ens/${ens}`;

    if (timestamp) {
      url += `?timestamp=${timestamp}`;
    }

    return url;
  };

  const clearEnsAvatarCache = async (
    listEns: string[] | null
  ): Promise<boolean> => {
    const response = await api.instance.post<ActionResult<boolean>>(
      '/cache/avatars/clear',
      { entries: listEns },
      {
        validateStatus: validStatus
      }
    );

    return handleResponse(response);
  };

  return {
    getEnsNamesTask,
    getEnsNames,
    fetchAddressBook,
    addAddressBook,
    updateAddressBook,
    deleteAddressBook,
    getAddressesNames,
    ensAvatarUrl,
    clearEnsAvatarCache
  };
};
