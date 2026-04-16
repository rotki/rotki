import { useSessionAuthStore } from '@/modules/auth/use-session-auth-store';
import { usePremium } from '@/modules/premium/use-premium';
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
