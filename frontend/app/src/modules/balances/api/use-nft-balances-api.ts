import type { PendingTask } from '@/modules/core/tasks/types';
import {
  NonFungibleBalancesCollectionResponse,
  type NonFungibleBalancesRequestPayload,
} from '@/modules/balances/types/nfbalances';
import { api } from '@/modules/core/api/rotki-api';
import { VALID_WITH_PARAMS_SESSION_AND_EXTERNAL_SERVICE } from '@/modules/core/api/utils';

interface UseNftBalancesApiReturn {
  fetchNfBalancesTask: (payload: NonFungibleBalancesRequestPayload) => Promise<PendingTask>;
  fetchNfBalances: (payload: NonFungibleBalancesRequestPayload) => Promise<NonFungibleBalancesCollectionResponse>;
}

export function useNftBalancesApi(): UseNftBalancesApiReturn {
  const internalNfBalances = async <T>(payload: NonFungibleBalancesRequestPayload, asyncQuery: boolean): Promise<T> => api.get<T>('/nfts/balances', {
    query: {
      asyncQuery,
      ...payload,
    },
    validStatuses: VALID_WITH_PARAMS_SESSION_AND_EXTERNAL_SERVICE,
  });

  const fetchNfBalancesTask = async (payload: NonFungibleBalancesRequestPayload): Promise<PendingTask> =>
    internalNfBalances<PendingTask>(payload, true);

  const fetchNfBalances = async (
    payload: NonFungibleBalancesRequestPayload,
  ): Promise<NonFungibleBalancesCollectionResponse> => {
    const response = await internalNfBalances<NonFungibleBalancesCollectionResponse>(
      payload,
      false,
    );

    return NonFungibleBalancesCollectionResponse.parse(response);
  };

  return {
    fetchNfBalances,
    fetchNfBalancesTask,
  };
}
