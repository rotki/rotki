import { usePremium } from '@/composables/premium';
import { useSessionAuthStore } from '@/modules/session/use-session-auth-store';
import { useStatisticsDataFetching } from '@/modules/statistics/use-statistics-data-fetching';

export function useStatisticsWatchers(): void {
  const premium = usePremium();
  const { logged } = storeToRefs(useSessionAuthStore());
  const { fetchNetValue } = useStatisticsDataFetching();

  watch(premium, async () => {
    if (get(logged))
      await fetchNetValue();
  });
}
