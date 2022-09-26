import { ActionResult } from '@rotki/common/lib/data';
import {
  axiosSnakeCaseTransformer,
  getUpdatedKey
} from '@/services/axios-tranformers';
import { basicAxiosTransformer } from '@/services/consts';
import { api } from '@/services/rotkehlchen-api';
import { PendingTask } from '@/services/types-api';
import {
  handleResponse,
  validWithSessionAndExternalService
} from '@/services/utils';
import {
  emptyPagination,
  KrakenStakingEvents,
  KrakenStakingPagination
} from '@/types/staking';

export const useKrakenApi = () => {
  const internalKrakenStaking = async <T>(
    pagination: KrakenStakingPagination,
    asyncQuery: boolean = false
  ): Promise<T> => {
    const response = await api.instance.post<ActionResult<T>>(
      '/staking/kraken',
      axiosSnakeCaseTransformer({
        asyncQuery,
        ...pagination,
        orderByAttributes:
          pagination.orderByAttributes?.map(item =>
            getUpdatedKey(item, false)
          ) ?? []
      }),
      {
        validateStatus: validWithSessionAndExternalService,
        transformResponse: basicAxiosTransformer
      }
    );
    return handleResponse(response);
  };

  const refreshKrakenStaking = async (): Promise<PendingTask> => {
    return await internalKrakenStaking(emptyPagination(), true);
  };

  const fetchKrakenStakingEvents = async (
    pagination: KrakenStakingPagination
  ): Promise<KrakenStakingEvents> => {
    const data = await internalKrakenStaking({
      ...pagination,
      onlyCache: true
    });
    return KrakenStakingEvents.parse(data);
  };

  return {
    refreshKrakenStaking,
    fetchKrakenStakingEvents
  };
};
