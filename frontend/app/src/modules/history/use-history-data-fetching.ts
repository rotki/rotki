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

export function useHistoryDataFetching(): UseHistoryDataFetchingReturn {
  const store = useHistoryStore();
  const { fetchAssociatedLocations: fetchAssociatedLocationsApi, fetchLocationLabels: fetchLocationLabelsApi } = useHistoryApi();
  const { getTransactionStatusSummary } = useHistoryEventsApi();
  const { notifyError } = useNotifications();
  const { t } = useI18n({ useScope: 'global' });

  async function fetchAssociatedLocations(): Promise<void> {
    try {
      store.setAssociatedLocations(await fetchAssociatedLocationsApi());
    }
    catch (error: unknown) {
      logger.error(error);
      notifyError(
        t('actions.history.fetch_associated_locations.error.title'),
        t('actions.history.fetch_associated_locations.error.message', { message: getErrorMessage(error) }),
      );
    }
  }

  async function fetchLocationLabels(): Promise<void> {
    try {
      store.setLocationLabels(await fetchLocationLabelsApi());
    }
    catch (error: unknown) {
      logger.error(error);
      notifyError(
        t('actions.history.fetch_location_labels.error.title'),
        t('actions.history.fetch_location_labels.error.message', { message: getErrorMessage(error) }),
      );
    }
  }

  async function fetchTransactionStatusSummary(): Promise<void> {
    try {
      const result: TransactionStatus = await getTransactionStatusSummary();
      store.setTransactionStatusSummary(result);
    }
    catch (error: unknown) {
      logger.error(error);
    }
  }

  return { fetchAssociatedLocations, fetchLocationLabels, fetchTransactionStatusSummary };
}
