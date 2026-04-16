import { getErrorMessage, useNotifications } from '@/modules/core/notifications/use-notifications';
import { useFrontendSettingsStore } from '@/modules/settings/use-frontend-settings-store';
import { useStatisticsApi } from '@/modules/statistics/api/use-statistics-api';
import { useStatisticsStore } from '@/modules/statistics/use-statistics-store';

interface UseStatisticsDataFetchingReturn {
  fetchNetValue: () => Promise<void>;
}

export function useStatisticsDataFetching(): UseStatisticsDataFetchingReturn {
  const { netValue } = storeToRefs(useStatisticsStore());
  const api = useStatisticsApi();
  const { notifyError } = useNotifications();
  const { nftsInNetValue } = storeToRefs(useFrontendSettingsStore());
  const { t } = useI18n({ useScope: 'global' });

  async function fetchNetValue(): Promise<void> {
    try {
      set(netValue, await api.queryNetValueData(get(nftsInNetValue)));
    }
    catch (error: unknown) {
      notifyError(t('actions.statistics.net_value.error.title'), t('actions.statistics.net_value.error.message', {
        message: getErrorMessage(error),
      }), { display: false });
    }
  }

  return { fetchNetValue };
}
