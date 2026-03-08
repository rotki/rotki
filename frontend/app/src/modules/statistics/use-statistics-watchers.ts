import { usePremium } from '@/composables/premium';
import { useStatisticsDataFetching } from '@/modules/statistics/use-statistics-data-fetching';
import { useSessionAuthStore } from '@/store/session/auth';

export function useStatisticsWatchers(): void {
  const premium = usePremium();
  const { logged } = storeToRefs(useSessionAuthStore());
  const { fetchNetValue } = useStatisticsDataFetching();

  watch(premium, async () => {
    if (get(logged))
      await fetchNetValue();
  });
}
