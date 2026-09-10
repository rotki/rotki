import { Priority } from '@rotki/common';
import { isRequestCancellation } from '@/modules/core/api/request-queue/is-request-cancellation';
import { getErrorMessage, useNotifications } from '@/modules/core/notifications/use-notifications';
import { useSetting } from '@/modules/settings/use-setting';
import { useStatisticsApi } from '@/modules/statistics/api/use-statistics-api';
import { useStatisticsStore } from '@/modules/statistics/use-statistics-store';

interface UseStatisticsDataFetchingReturn {
  fetchNetValue: () => Promise<void>;
}

export function useStatisticsDataFetching(): UseStatisticsDataFetchingReturn {
  const statisticsStore = useStatisticsStore();
  const { netValue } = storeToRefs(statisticsStore);
  const { setNetValueError } = statisticsStore;
  const api = useStatisticsApi();
  const { notifyError } = useNotifications();
  const nftsInNetValue = useSetting('nftsInNetValue');
  const { t } = useI18n({ useScope: 'global' });

  async function fetchNetValue(): Promise<void> {
    try {
      set(netValue, await api.queryNetValueData(get(nftsInNetValue)));
      setNetValueError(undefined);
    }
    catch (error: unknown) {
      // A cancelled request is the queue dropping work, not a failure the chart should report.
      if (isRequestCancellation(error))
        return;

      const message = getErrorMessage(error);
      setNetValueError(message);
      notifyError(t('actions.statistics.net_value.error.title'), t('actions.statistics.net_value.error.message', {
        message,
      }), { priority: Priority.NORMAL });
    }
  }

  return { fetchNetValue };
}
