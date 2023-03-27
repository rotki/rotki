import { type ActionResult } from '@rotki/common/lib/data';
import {
  getUpdatedKey,
  snakeCaseTransformer
} from '@/services/axios-tranformers';
import { api } from '@/services/rotkehlchen-api';
import {
  handleResponse,
  validWithSessionAndExternalService
} from '@/services/utils';
import {
  KrakenStakingEvents,
  type KrakenStakingPagination,
  emptyPagination
} from '@/types/staking';
import { type PendingTask } from '@/types/task';

export const useKrakenApi = () => {
  const internalKrakenStaking = async <T>(
    pagination: KrakenStakingPagination,
    asyncQuery = false
  ): Promise<T> => {
    const response = await api.instance.post<ActionResult<T>>(
      '/staking/kraken',
      snakeCaseTransformer({
        asyncQuery,
        ...pagination,
        orderByAttributes:
          pagination.orderByAttributes?.map(item =>
            getUpdatedKey(item, false)
          ) ?? []
      }),
      {
        validateStatus: validWithSessionAndExternalService
      }
    );
    return handleResponse(response);
  };

  const refreshKrakenStaking = async (): Promise<PendingTask> =>
    await internalKrakenStaking(emptyPagination(), true);

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
