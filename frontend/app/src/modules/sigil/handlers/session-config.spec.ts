import { Theme } from '@rotki/common';
import { beforeEach, describe, expect, it } from 'vitest';

describe('useSessionConfigHandler', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
  });

  it('should collect session config from stores', async () => {
    const { usePremiumStore } = await import('@/store/session/premium');
    const { useGeneralSettingsStore } = await import('@/store/settings/general');
    const { useFrontendSettingsStore } = await import('@/store/settings/frontend');

    const { premium } = storeToRefs(usePremiumStore());
    set(premium, true);

    const generalStore = useGeneralSettingsStore();
    generalStore.$patch({
      settings: {
        submitUsageAnalytics: true,
        mainCurrency: { tickerSymbol: 'EUR' },
        currentPriceOracles: ['coingecko', 'cryptocompare'],
      },
    } as any);

    const frontendStore = useFrontendSettingsStore();
    frontendStore.$patch({
      settings: {
        language: 'es',
        selectedTheme: Theme.DARK,
      },
    } as any);

    const { useSessionConfigHandler } = await import('@/modules/sigil/handlers/session-config');
    const collect = useSessionConfigHandler();
    const result = collect();

    expect(result.premium).toBe(true);
    expect(result.mainCurrency).toBe('EUR');
    expect(result.language).toBe('es');
    expect(result.theme).toBe('dark');
    expect(result.priceOracles).toBe('coingecko,cryptocompare');
    expect(result.appMode).toBeDefined();
  });
});
