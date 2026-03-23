import { beforeEach, describe, expect, it } from 'vitest';

describe('useExchangesSummaryHandler', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
  });

  it('should return zero counts when no exchanges connected', async () => {
    const { useExchangesSummaryHandler } = await import('@/modules/sigil/handlers/exchanges-summary');
    const collect = useExchangesSummaryHandler();
    const result = collect();

    expect(result.premium).toBe(false);
    expect(result.plan).toBe('Free');
    expect(result.exchangeCount).toBe(0);
  });

  it('should count exchanges by location', async () => {
    const { useSessionSettingsStore } = await import('@/store/settings/session');
    const store = useSessionSettingsStore();
    const { connectedExchanges } = storeToRefs(store);

    set(connectedExchanges, [
      { location: 'binance', name: 'binance1' },
      { location: 'binance', name: 'binance2' },
      { location: 'kraken', name: 'kraken1' },
    ] as any);

    const { useExchangesSummaryHandler } = await import('@/modules/sigil/handlers/exchanges-summary');
    const collect = useExchangesSummaryHandler();
    const result = collect();

    expect(result.exchangeCount).toBe(3);
    expect(result.exchange_binance).toBe(2);
    expect(result.exchange_kraken).toBe(1);
  });
});
