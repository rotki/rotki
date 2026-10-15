import type { MaybeRefOrGetter, Ref } from 'vue';
import { get, set } from '@vueuse/shared';
import { logger } from '@/modules/core/common/logging/logging';
import { useWrapStatisticsApi, type WrapStatisticsResult } from '@/modules/statistics/api/use-wrap-statistics-api';

interface UseWrappedStatisticsReturn {
  fetchData: () => Promise<void>;
  loading: Readonly<Ref<boolean>>;
  summary: Readonly<Ref<WrapStatisticsResult | null | undefined>>;
}

export function useWrappedStatistics(
  start: MaybeRefOrGetter<number>,
  end: MaybeRefOrGetter<number>,
  refreshing: MaybeRefOrGetter<boolean>,
): UseWrappedStatisticsReturn {
  const { fetchWrapStatistics } = useWrapStatisticsApi();

  const loading = shallowRef<boolean>(false);
  const summary = ref<WrapStatisticsResult | null>();

  /** A fetch asked for while one runs: the range changed under it, so it runs again after. */
  let refetch = false;

  async function fetchData(): Promise<void> {
    if (get(loading)) {
      refetch = true;
      return;
    }

    try {
      const endVal = toValue(end);
      const startVal = toValue(start);

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

    if (refetch) {
      refetch = false;
      await fetchData();
    }
  }

  watch(() => toValue(refreshing), async (curr, old) => {
    if (old && !curr) {
      await fetchData();
    }
  });

  return {
    fetchData,
    loading: readonly(loading),
    summary: shallowReadonly(summary),
  };
}
