import type { ExchangesSummaryPayload } from '@/modules/core/sigil/types';
import { useConnectedExchangesStore } from '@/modules/balances/exchanges/use-connected-exchanges-store';
import { usePremiumHelper } from '@/modules/premium/use-premium-helper';

export function useExchangesSummaryHandler(): () => ExchangesSummaryPayload {
  const { currentTier, premium } = usePremiumHelper();
  const { connectedExchanges } = storeToRefs(useConnectedExchangesStore());

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
