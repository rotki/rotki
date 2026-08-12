import type { PendingTask } from '@/modules/core/tasks/types';
import { transformCase } from '@rotki/common';
import { api } from '@/modules/core/api/rotki-api';
import { VALID_WITH_SESSION_AND_EXTERNAL_SERVICE } from '@/modules/core/api/utils';
import { emptyPagination, KrakenStakingEvents, type KrakenStakingPagination } from '@/modules/staking/staking-types';

/**
 * Tags the cached read so a newer one can cancel the read it supersedes. Only the cached read
 * carries it: the refresh is a backend task, not something to abort because the filter moved.
 *
 * Deliberately not exported. Callers cancel through `cancelPendingEventReads`, so the tag is not a
 * string that has to be spelled identically in two modules to work, and nothing outside can enqueue
 * a request under it.
 */
const KRAKEN_STAKING_CANCEL_TAG = 'kraken-staking-events';

interface UseKrakenApiReturn {
  refreshKrakenStaking: () => Promise<PendingTask>;
  fetchKrakenStakingEvents: (pagination: KrakenStakingPagination) => Promise<KrakenStakingEvents>;
  cancelPendingEventReads: () => void;
}

interface KrakenStakingRequestOptions {
  /** Hand the query to the backend as a task instead of answering it inline. */
  asyncQuery?: boolean;
  /** Cancellation tags the request is enqueued under. */
  tags?: string[];
}

export function useKrakenApi(): UseKrakenApiReturn {
  const internalKrakenStaking = async <T>(
    pagination: KrakenStakingPagination,
    { asyncQuery = false, tags }: KrakenStakingRequestOptions = {},
  ): Promise<T> => api.post<T>(
    '/staking/kraken',
    {
      asyncQuery,
      ...pagination,
      orderByAttributes: pagination.orderByAttributes?.map(item => transformCase(item)) ?? [],
    },
    {
      tags,
      validStatuses: VALID_WITH_SESSION_AND_EXTERNAL_SERVICE,
    },
  );

  const refreshKrakenStaking = async (): Promise<PendingTask> =>
    internalKrakenStaking(emptyPagination(), { asyncQuery: true });

  const fetchKrakenStakingEvents = async (pagination: KrakenStakingPagination): Promise<KrakenStakingEvents> => {
    const data = await internalKrakenStaking({
      ...pagination,
      onlyCache: true,
    }, { tags: [KRAKEN_STAKING_CANCEL_TAG] });
    return KrakenStakingEvents.parse(data);
  };

  /** Aborts any cached read still in flight, so it cannot land on top of a newer one. */
  const cancelPendingEventReads = (): void => {
    api.cancelByTag(KRAKEN_STAKING_CANCEL_TAG);
  };

  return {
    cancelPendingEventReads,
    fetchKrakenStakingEvents,
    refreshKrakenStaking,
  };
}
