import type { HistorySyncPayload } from '@/modules/core/sigil/types';
import { logger } from '@/modules/core/common/logging/logging';
import { useHistoryEventsApi } from '@/modules/history/api/events/use-history-events-api';
import { usePremiumHelper } from '@/modules/premium/use-premium-helper';

export function useHistorySyncHandler(): () => Promise<HistorySyncPayload | undefined> {
  const { currentTier, premium } = usePremiumHelper();
  const { fetchHistoryEvents } = useHistoryEventsApi();

  return async () => {
    try {
      const [eventsResult, groupsResult] = await Promise.all([
        fetchHistoryEvents({
          limit: 1,
          offset: 0,
          aggregateByGroupIds: false,
          excludeIgnoredAssets: true,
        }),
        fetchHistoryEvents({
          limit: 1,
          offset: 0,
          aggregateByGroupIds: true,
          excludeIgnoredAssets: true,
        }),
      ]);
      const totalEvents = eventsResult.entriesTotal;
      const nonSpamEvents = eventsResult.entriesFound;
      return {
        premium: get(premium),
        plan: get(currentTier),
        totalEvents,
        spamEvents: totalEvents - nonSpamEvents,
        totalGroups: groupsResult.entriesFound,
      };
    }
    catch {
      logger.debug('[sigil] failed to fetch event count for history sync');
      return undefined;
    }
  };
}
