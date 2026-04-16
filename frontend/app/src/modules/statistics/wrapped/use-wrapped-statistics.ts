import type { Ref } from 'vue';
import { get, set } from '@vueuse/shared';
import { logger } from '@/modules/core/common/logging/logging';
import { useWrapStatisticsApi, type WrapStatisticsResult } from '@/modules/statistics/api/use-wrap-statistics-api';

interface UseWrappedStatisticsReturn {
  fetchData: () => Promise<void>;
  loading: Ref<boolean>;
  summary: Ref<WrapStatisticsResult | null | undefined>;
}

export function useWrappedStatistics(
  start: Ref<number>,
  end: Ref<number>,
  refreshing: Ref<boolean>,
): UseWrappedStatisticsReturn {
  const { fetchWrapStatistics } = useWrapStatisticsApi();

  const loading = ref<boolean>(false);
  const summary = ref<WrapStatisticsResult | null>();

  async function fetchData(): Promise<void> {
    if (get(loading))
      return;

    try {
      const endVal = get(end);
      const startVal = get(start);

      set(loading, true);
      const response = await fetchWrapStatistics({
        end: endVal,
        start: startVal,
      });
      set(summary, response);
    }
    catch (error) {
      logger.error(error);
      set(summary, null);
    }
    finally {
      set(loading, false);
    }
  }

  watch(refreshing, async (curr, old) => {
    if (old && !curr) {
      await fetchData();
    }
  });

  return {
    fetchData,
    loading,
    summary,
  };
}
