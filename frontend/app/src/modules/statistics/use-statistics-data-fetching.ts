import { isRequestCancellation } from '@/modules/core/api/request-queue/is-request-cancellation';
import { logger } from '@/modules/core/common/logging/logging';
import { getErrorMessage } from '@/modules/core/notifications/use-notifications';
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
  const nftsInNetValue = useSetting('nftsInNetValue');

  /**
   * Reads the net value history, keeping a failure for the chart to show in its place.
   *
   * @remarks
   * A cancelled request is the queue dropping work, not a failure the chart should report.
   */
  async function fetchNetValue(): Promise<void> {
    try {
      set(netValue, await api.queryNetValueData(get(nftsInNetValue)));
      setNetValueError(undefined);
    }
    catch (error: unknown) {
      if (isRequestCancellation(error))
        return;

      logger.error(error);
      setNetValueError(getErrorMessage(error));
    }
  }

  return { fetchNetValue };
}
