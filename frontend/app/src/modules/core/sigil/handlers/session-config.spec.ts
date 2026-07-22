import { Theme } from '@rotki/common';
import { beforeEach, describe, expect, it } from 'vitest';
import { SupportedLanguage } from '@/modules/settings/types/frontend-settings';

describe('useSessionConfigHandler', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
  });

  it('should collect session config from stores', async () => {
    const { usePremiumStore } = await import('@/modules/premium/use-premium-store');
    const { useSettingsRepo } = await import('@/modules/settings/settings-repo');

    const { premium } = storeToRefs(usePremiumStore());
    set(premium, true);

    const generalStore = useSettingsRepo();
    generalStore.$patch({
      general: {
        submitUsageAnalytics: true,
        mainCurrency: { tickerSymbol: 'EUR' },
        currentPriceOracles: ['coingecko', 'cryptocompare'],
      },
    });

    const frontendStore = useSettingsRepo();
    frontendStore.$patch({
      frontend: {
        language: SupportedLanguage.ES,
        selectedTheme: Theme.DARK,
      },
    });

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
