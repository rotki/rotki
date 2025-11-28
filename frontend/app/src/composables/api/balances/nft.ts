import type { ActionResult } from '@rotki/common';
import type { PendingTask } from '@/types/task';
import { snakeCaseTransformer } from '@/services/axios-transformers';
import { api } from '@/services/rotkehlchen-api';
import {
  handleResponse,
  paramsSerializer,
  validWithParamsSessionAndExternalService,
} from '@/services/utils';
import {
  NonFungibleBalancesCollectionResponse,
  type NonFungibleBalancesRequestPayload,
} from '@/types/nfbalances';

interface UseNftBalancesApiReturn {
  fetchNfBalancesTask: (payload: NonFungibleBalancesRequestPayload) => Promise<PendingTask>;
  fetchNfBalances: (payload: NonFungibleBalancesRequestPayload) => Promise<NonFungibleBalancesCollectionResponse>;
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

  return {
    fetchNfBalances,
    fetchNfBalancesTask,
  };
}
