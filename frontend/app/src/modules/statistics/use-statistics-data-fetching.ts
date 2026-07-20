import { isRequestCancellation } from '@/modules/core/api/request-queue/is-request-cancellation';
import { getErrorMessage, useNotifications } from '@/modules/core/notifications/use-notifications';
import { useSetting } from '@/modules/settings/use-setting';
import { useStatisticsApi } from '@/modules/statistics/api/use-statistics-api';
import { useStatisticsStore } from '@/modules/statistics/use-statistics-store';

interface UseStatisticsDataFetchingReturn {
  fetchNetValue: () => Promise<void>;
}

export function useStatisticsDataFetching(): UseStatisticsDataFetchingReturn {
  const { netValue } = storeToRefs(useStatisticsStore());
  const api = useStatisticsApi();
  const { notifyError } = useNotifications();
  const nftsInNetValue = useSetting('nftsInNetValue');
  const { t } = useI18n({ useScope: 'global' });

  async function fetchNetValue(): Promise<void> {
    try {
      set(netValue, await api.queryNetValueData(get(nftsInNetValue)));
    }
    catch (error: unknown) {
      if (isRequestCancellation(error))
        return;

      notifyError(t('actions.statistics.net_value.error.title'), t('actions.statistics.net_value.error.message', {
        message: getErrorMessage(error),
      }), { display: false });
    }
  }

  return { fetchNetValue };
}
