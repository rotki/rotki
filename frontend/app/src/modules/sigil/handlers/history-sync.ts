import type { HistorySyncPayload } from '@/modules/sigil/types';
import { useHistoryEventsApi } from '@/composables/api/history/events';
import { usePremiumHelper } from '@/composables/premium';
import { logger } from '@/utils/logging';

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
