import { Theme } from '@rotki/common';
import { beforeEach, describe, expect, it } from 'vitest';

describe('useSessionConfigHandler', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
  });

  it('should collect session config from stores', async () => {
    const { usePremiumStore } = await import('@/modules/premium/use-premium-store');
    const { useGeneralSettingsStore } = await import('@/modules/settings/use-general-settings-store');
    const { useFrontendSettingsStore } = await import('@/modules/settings/use-frontend-settings-store');

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

    const { useSessionConfigHandler } = await import('@/modules/core/sigil/handlers/session-config');
    const collect = useSessionConfigHandler();
    const result = collect();

    expect(result.premium).toBe(true);
    expect(result.plan).toBe('Free');
    expect(result.mainCurrency).toBe('EUR');
    expect(result.language).toBe('es');
    expect(result.theme).toBe('dark');
    expect(result.priceOracles).toBe('coingecko,cryptocompare');
    expect(result.appMode).toBeDefined();
  });
});
