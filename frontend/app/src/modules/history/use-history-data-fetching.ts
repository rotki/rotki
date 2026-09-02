import { isRequestCancellation } from '@/modules/core/api/request-queue/is-request-cancellation';
import { getErrorMessage } from '@/modules/core/common/logging/error-handling';
import { logger } from '@/modules/core/common/logging/logging';
import { useNotifications } from '@/modules/core/notifications/use-notifications';
import { type TransactionStatus, useHistoryEventsApi } from '@/modules/history/api/events/use-history-events-api';
import { useHistoryApi } from '@/modules/history/api/use-history-api';
import { useHistoryStore } from '@/modules/history/use-history-store';

interface UseHistoryDataFetchingReturn {
  fetchAssociatedLocations: () => Promise<void>;
  fetchLocationLabels: () => Promise<void>;
  fetchTransactionStatusSummary: () => Promise<void>;
}

/**
 * In-flight reads, shared across every caller of this composable.
 *
 * One flow ending produces several reads of the location set — the redecode handler, the auto-fetch
 * and a modification watcher can all fire around the same boundary, and none can see the others.
 *
 * Joining rather than caching: a caller always gets a promise resolving once the data is current, so
 * nothing is skipped and only genuinely concurrent reads collapse.
 *
 * Module scope, not composable scope: `useHistoryDataFetching` is a plain function, so each caller
 * gets its own closure and per-instance state would not be shared.
 */
const inFlight = new Map<string, Promise<void>>();

async function join(key: string, run: () => Promise<void>): Promise<void> {
  const current = inFlight.get(key);
  if (current)
    return current;

  // Clears only its own entry, so a request started after this one settles is never dropped.
  const request = run().finally(() => {
    if (inFlight.get(key) === request)
      inFlight.delete(key);
  });
  inFlight.set(key, request);
  return request;
}

export function useHistoryDataFetching(): UseHistoryDataFetchingReturn {
  const store = useHistoryStore();
  const { fetchAssociatedLocations: fetchAssociatedLocationsApi, fetchLocationLabels: fetchLocationLabelsApi } = useHistoryApi();
  const { getTransactionStatusSummary } = useHistoryEventsApi();
  const { notifyError } = useNotifications();
  const { t } = useI18n({ useScope: 'global' });

  async function readAssociatedLocations(): Promise<void> {
    try {
      store.setAssociatedLocations(await fetchAssociatedLocationsApi());
    }
    catch (error: unknown) {
      if (isRequestCancellation(error))
        return;

      logger.error(error);
      notifyError(
        t('actions.history.fetch_associated_locations.error.title'),
        t('actions.history.fetch_associated_locations.error.message', { message: getErrorMessage(error) }),
      );
    }
  }

  async function readLocationLabels(): Promise<void> {
    try {
      store.setLocationLabels(await fetchLocationLabelsApi());
    }
    catch (error: unknown) {
      if (isRequestCancellation(error))
        return;

      logger.error(error);
      notifyError(
        t('actions.history.fetch_location_labels.error.title'),
        t('actions.history.fetch_location_labels.error.message', { message: getErrorMessage(error) }),
      );
    }
  }

  async function fetchAssociatedLocations(): Promise<void> {
    return join('associated-locations', readAssociatedLocations);
  }

  async function fetchLocationLabels(): Promise<void> {
    return join('location-labels', readLocationLabels);
  }

  async function fetchTransactionStatusSummary(): Promise<void> {
    try {
      const result: TransactionStatus = await getTransactionStatusSummary();
      store.setTransactionStatusSummary(result);
    }
    catch (error: unknown) {
      if (isRequestCancellation(error))
        return;

      logger.error(error);
    }
  }

  return { fetchAssociatedLocations, fetchLocationLabels, fetchTransactionStatusSummary };
}
