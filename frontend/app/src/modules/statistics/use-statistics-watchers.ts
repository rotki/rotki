import { useSessionAuthStore } from '@/modules/auth/use-session-auth-store';
import { usePremium } from '@/modules/premium/use-premium';
import { useSnapshotRates } from '@/modules/statistics/pricing/use-snapshot-rates';
import { useStatisticsDataFetching } from '@/modules/statistics/use-statistics-data-fetching';

export function useStatisticsWatchers(): void {
  const premium = usePremium();
  const { logged } = storeToRefs(useSessionAuthStore());
  const { fetchNetValue } = useStatisticsDataFetching();

  useSnapshotRates();

  watch(premium, async () => {
    if (get(logged))
      await fetchNetValue();
  });
}
