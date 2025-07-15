import type { ActionResult } from '@rotki/common';
import type { PendingTask } from '@/types/task';
import { snakeCaseTransformer } from '@/services/axios-transformers';
import { api } from '@/services/rotkehlchen-api';
import {
  handleResponse,
  paramsSerializer,
  validStatus,
  validWithParamsSessionAndExternalService,
} from '@/services/utils';
import {
  NonFungibleBalance,
  NonFungibleBalancesCollectionResponse,
  type NonFungibleBalancesRequestPayload,
} from '@/types/nfbalances';

interface UseNftBalancesApiReturn {
  fetchNfBalancesTask: (payload: NonFungibleBalancesRequestPayload) => Promise<PendingTask>;
  fetchNfBalances: (payload: NonFungibleBalancesRequestPayload) => Promise<NonFungibleBalancesCollectionResponse>;
  getNftBalanceById: (identifier: string) => Promise<NonFungibleBalance>;
}

export function useNftBalancesApi(): UseNftBalancesApiReturn {
  const internalNfBalances = async <T>(payload: NonFungibleBalancesRequestPayload, asyncQuery: boolean): Promise<T> => {
    const response = await api.instance.get<ActionResult<T>>('/nfts/balances', {
      params: snakeCaseTransformer({
        asyncQuery,
        ...payload,
      }),
      paramsSerializer,
      validateStatus: validWithParamsSessionAndExternalService,
    });

    return handleResponse(response);
  };

  const fetchNfBalancesTask = async (payload: NonFungibleBalancesRequestPayload): Promise<PendingTask> =>
    internalNfBalances<PendingTask>(payload, true);

  const fetchNfBalances = async (
    payload: NonFungibleBalancesRequestPayload,
  ): Promise<NonFungibleBalancesCollectionResponse> => {
    const response = await internalNfBalances<NonFungibleBalancesCollectionResponse>(
      snakeCaseTransformer(payload),
      false,
    );

    return NonFungibleBalancesCollectionResponse.parse(response);
  };

  const getNftBalanceById = async (identifier: string): Promise<NonFungibleBalance> => {
    const response = await api.instance.post<ActionResult<NonFungibleBalance>>(
      '/nfts',
      {
        nftId: identifier,
      },
      {
        validateStatus: validStatus,
      },
    );

    return NonFungibleBalance.parse(response);
  };

  return {
    fetchNfBalances,
    fetchNfBalancesTask,
    getNftBalanceById,
  };
}
