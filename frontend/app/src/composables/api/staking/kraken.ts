import type { PendingTask } from '@/types/task';
import { snakeCaseTransformer } from '@/services/axios-transformers';
import { api } from '@/services/rotkehlchen-api';
import { handleResponse, validWithSessionAndExternalService } from '@/services/utils';
import { emptyPagination, KrakenStakingEvents, type KrakenStakingPagination } from '@/types/staking';
import { type ActionResult, transformCase } from '@rotki/common';

interface UseKrakenApiReturn {
  refreshKrakenStaking: () => Promise<PendingTask>;
  fetchKrakenStakingEvents: (pagination: KrakenStakingPagination) => Promise<KrakenStakingEvents>;
}

export function useKrakenApi(): UseKrakenApiReturn {
  const internalKrakenStaking = async <T>(pagination: KrakenStakingPagination, asyncQuery = false): Promise<T> => {
    const response = await api.instance.post<ActionResult<T>>(
      '/staking/kraken',
      snakeCaseTransformer({
        asyncQuery,
        ...pagination,
        orderByAttributes: pagination.orderByAttributes?.map(item => transformCase(item)) ?? [],
      }),
      {
        validateStatus: validWithSessionAndExternalService,
      },
    );
    return handleResponse(response);
  };

  const refreshKrakenStaking = async (): Promise<PendingTask> => internalKrakenStaking(emptyPagination(), true);

  const fetchKrakenStakingEvents = async (pagination: KrakenStakingPagination): Promise<KrakenStakingEvents> => {
    const data = await internalKrakenStaking({
      ...pagination,
      onlyCache: true,
    });
    return KrakenStakingEvents.parse(data);
  };

  return {
    fetchKrakenStakingEvents,
    refreshKrakenStaking,
  };
}
