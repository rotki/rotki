import { ActionResult } from '@rotki/common/lib/data';
import { axiosSnakeCaseTransformer } from '@/services/axios-tranformers';
import { api } from '@/services/rotkehlchen-api';
import { PendingTask } from '@/services/types-api';
import {
  handleResponse,
  validWithSessionAndExternalService
} from '@/services/utils';
import {
  EthAddressBookLocation,
  EthNames,
  EthNamesEntries
} from '@/types/eth-names';

export const useEthNamesApi = () => {
  const internalEnsNames = async <T>(
    ethereumAddresses: string[],
    asyncQuery = false
  ): Promise<T> => {
    const response = await api.instance.post<ActionResult<T>>(
      '/names/ens/reverse',
      axiosSnakeCaseTransformer({
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

  const getEthAddressBook = async (
    location: EthAddressBookLocation,
    addresses?: string[]
  ): Promise<EthNamesEntries> => {
    const response = await api.instance.post<ActionResult<EthNames>>(
      `/names/addressbook/${location}`,
      addresses ? { addresses } : null,
      {
        validateStatus: validWithSessionAndExternalService
      }
    );

    return EthNamesEntries.parse(handleResponse(response));
  };

  const addEthAddressBook = async (
    location: EthAddressBookLocation,
    entries: EthNamesEntries
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

  const updateEthAddressBook = async (
    location: EthAddressBookLocation,
    entries: EthNamesEntries
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

  const deleteEthAddressBook = async (
    location: EthAddressBookLocation,
    addresses: string[]
  ): Promise<boolean> => {
    const response = await api.instance.delete<ActionResult<boolean>>(
      `/names/addressbook/${location}`,
      {
        data: axiosSnakeCaseTransformer({ addresses }),
        validateStatus: validWithSessionAndExternalService
      }
    );

    return handleResponse(response);
  };

  const getEthNames = async (addresses: string[]): Promise<EthNames> => {
    const response = await api.instance.post<ActionResult<EthNames>>(
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
    getEthAddressBook,
    addEthAddressBook,
    updateEthAddressBook,
    deleteEthAddressBook,
    getEthNames
  };
};
