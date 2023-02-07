import { type ActionResult } from '@rotki/common/lib/data';
import { axiosSnakeCaseTransformer } from '@/services/axios-tranformers';
import { api } from '@/services/rotkehlchen-api';
import {
  handleResponse,
  paramsSerializer,
  validStatus,
  validWithParamsSessionAndExternalService
} from '@/services/utils';
import {
  NonFungibleBalance,
  NonFungibleBalancesCollectionResponse,
  type NonFungibleBalancesRequestPayload
} from '@/types/nfbalances';
import { type PendingTask } from '@/types/task';

export const useNftBalancesApi = () => {
  const internalNfBalances = async <T>(
    payload: NonFungibleBalancesRequestPayload,
    asyncQuery: boolean
  ): Promise<T> => {
    const response = await api.instance.get<ActionResult<T>>('/nfts/balances', {
      params: axiosSnakeCaseTransformer({
        asyncQuery,
        ...payload
      }),
      paramsSerializer,
      validateStatus: validWithParamsSessionAndExternalService
    });

    return handleResponse(response);
  };

  const fetchNfBalancesTask = async (
    payload: NonFungibleBalancesRequestPayload
  ): Promise<PendingTask> => {
    return internalNfBalances<PendingTask>(payload, true);
  };

  const fetchNfBalances = async (
    payload: NonFungibleBalancesRequestPayload
  ): Promise<NonFungibleBalancesCollectionResponse> => {
    const response =
      await internalNfBalances<NonFungibleBalancesCollectionResponse>(
        payload,
        false
      );

    return NonFungibleBalancesCollectionResponse.parse(response);
  };

  const getNftBalanceById = async (
    identifier: string
  ): Promise<NonFungibleBalance> => {
    const response = await api.instance.post<ActionResult<NonFungibleBalance>>(
      '/nfts',
      {
        nftId: identifier
      },
      {
        validateStatus: validStatus
      }
    );

    return NonFungibleBalance.parse(response);
  };

  return {
    fetchNfBalancesTask,
    fetchNfBalances,
    getNftBalanceById
  };
};
