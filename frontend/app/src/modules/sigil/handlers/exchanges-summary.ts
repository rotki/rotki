import type { ExchangesSummaryPayload } from '@/modules/sigil/types';
import { useSessionSettingsStore } from '@/store/settings/session';

export function useExchangesSummaryHandler(): () => ExchangesSummaryPayload {
  const { connectedExchanges } = storeToRefs(useSessionSettingsStore());

  return () => {
    const exchanges = get(connectedExchanges);
    const exchangeCounts: Record<string, number> = {};
    for (const ex of exchanges) {
      const key = `exchange_${ex.location}`;
      exchangeCounts[key] = (exchangeCounts[key] ?? 0) + 1;
    }

    return {
      exchangeCount: exchanges.length,
      ...exchangeCounts,
    };
  };
}
