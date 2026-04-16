import type { ExchangesSummaryPayload } from '@/modules/sigil/types';
import { usePremiumHelper } from '@/composables/premium';
import { useSessionSettingsStore } from '@/modules/settings/use-session-settings-store';

export function useExchangesSummaryHandler(): () => ExchangesSummaryPayload {
  const { currentTier, premium } = usePremiumHelper();
  const { connectedExchanges } = storeToRefs(useSessionSettingsStore());

  return () => {
    const exchanges = get(connectedExchanges);
    const exchangeCounts: Record<string, number> = {};
    for (const ex of exchanges) {
      const key = `exchange_${ex.location}`;
      exchangeCounts[key] = (exchangeCounts[key] ?? 0) + 1;
    }

    return {
      premium: get(premium),
      plan: get(currentTier),
      exchangeCount: exchanges.length,
      ...exchangeCounts,
    };
  };
}
