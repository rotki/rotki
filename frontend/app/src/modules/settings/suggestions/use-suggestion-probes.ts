import type { SuggestionProbes } from './settings-suggestions';
import type { ExternalServiceKeys } from '@/modules/integrations/types';
import { logger } from '@/modules/core/common/logging/logging';
import { useHistoryEventsApi } from '@/modules/history/api/events/use-history-events-api';
import { useExternalServicesApi } from '@/modules/settings/api/use-external-services-api';

/** Tag every probe carries so logging out can cancel whatever is still queued. */
export const SUGGESTION_PROBE_TAG = 'settings-suggestions';

/**
 * One run's probes, plus whether any of them fell over.
 *
 * The distinction matters because a provider that returns no suggestion is saying either "this user
 * does not need the question" or "I could not find out", and only the first is safe to record as
 * settled. Failing closed makes them look identical from the outside, so the probe set is what
 * remembers.
 */
interface ProbeRun {
  probes: SuggestionProbes;
  failed: () => boolean;
}

interface UseSuggestionProbesReturn {
  /** A fresh, memoized probe set for one run. Settings change between logins, answers must not. */
  createProbes: () => ProbeRun;
}

/**
 * The network half of the suggestion pipeline, kept behind the `SuggestionProbes` interface so
 * providers can be tested with a plain object instead of module mocks.
 *
 * Every probe fails closed: a suggestion that cannot prove it applies to this user is not shown,
 * which is the safe direction when the alternative is asking everyone.
 */
export function useSuggestionProbes(): UseSuggestionProbesReturn {
  const { fetchHistoryEvents } = useHistoryEventsApi();
  const { queryExternalServices } = useExternalServicesApi();

  function createProbes(): ProbeRun {
    const events = new Map<string, Promise<boolean>>();
    let keys: Promise<ExternalServiceKeys | undefined> | undefined;
    let failed = false;

    const probes: SuggestionProbes = {
      apiKeys: async (): Promise<ExternalServiceKeys | undefined> => {
        keys ??= queryExternalServices({ tags: [SUGGESTION_PROBE_TAG] }).catch((error: unknown) => {
          logger.error(error);
          failed = true;
          return undefined;
        });
        return keys;
      },
      hasEvents: async (location: string): Promise<boolean> => {
        const cached = events.get(location);
        if (cached)
          return cached;

        const pending = fetchHistoryEvents({
          aggregateByGroupIds: false,
          limit: 1,
          location,
          offset: 0,
        }, { tags: [SUGGESTION_PROBE_TAG] })
          .then(({ entriesFound }) => entriesFound > 0)
          .catch((error: unknown) => {
            logger.error(error);
            failed = true;
            return false;
          });

        events.set(location, pending);
        return pending;
      },
    };

    return { failed: (): boolean => failed, probes };
  }

  return { createProbes };
}
