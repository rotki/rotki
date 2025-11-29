import type { PendingTask } from '@/types/task';
import { transformCase } from '@rotki/common';
import { api } from '@/modules/api/rotki-api';
import { VALID_WITH_SESSION_AND_EXTERNAL_SERVICE } from '@/modules/api/utils';
import { emptyPagination, KrakenStakingEvents, type KrakenStakingPagination } from '@/types/staking';

interface UseKrakenApiReturn {
  refreshKrakenStaking: () => Promise<PendingTask>;
  fetchKrakenStakingEvents: (pagination: KrakenStakingPagination) => Promise<KrakenStakingEvents>;
}

export function useKrakenApi(): UseKrakenApiReturn {
  const internalKrakenStaking = async <T>(pagination: KrakenStakingPagination, asyncQuery = false): Promise<T> => api.post<T>(
    '/staking/kraken',
    {
      asyncQuery,
      ...pagination,
      orderByAttributes: pagination.orderByAttributes?.map(item => transformCase(item)) ?? [],
    },
    {
      validStatuses: VALID_WITH_SESSION_AND_EXTERNAL_SERVICE,
    },
  );

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
