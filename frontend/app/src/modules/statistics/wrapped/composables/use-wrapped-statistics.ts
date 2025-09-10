import type { Ref } from 'vue';
import { get, set } from '@vueuse/shared';
import { useWrapStatisticsApi, type WrapStatisticsResult } from '@/composables/api/statistics/wrap';
import { logger } from '@/utils/logging';

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
