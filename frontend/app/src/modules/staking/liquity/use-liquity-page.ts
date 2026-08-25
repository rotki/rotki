import type { Ref } from 'vue';
import { useHistoricCachePriceStore } from '@/modules/assets/prices/use-historic-cache-price-store';
import { usePriceTaskManager } from '@/modules/assets/prices/use-price-task-manager';
import { usePremium } from '@/modules/premium/use-premium';
import { Module, useModuleEnabled } from '@/modules/session/use-module-enabled';
import { useSetting } from '@/modules/settings/use-setting';
import { LIQUITY_PRICED_ASSETS } from '@/modules/staking/liquity/liquity-assets';
import { useLiquityDataFetching } from '@/modules/staking/liquity/use-liquity-data-fetching';

/** The modules this page depends on, as the module components expect them. */
export const LIQUITY_MODULES = [Module.LIQUITY];

interface UseLiquityPageReturn {
  fetch: (refresh?: boolean) => Promise<void>;
  moduleEnabled: Readonly<Ref<boolean>>;
  premium: Ref<boolean>;
}

export function useLiquityPage(): UseLiquityPageReturn {
  const { enabled: moduleEnabled } = useModuleEnabled(Module.LIQUITY);
  const { fetchPools, fetchStaking, fetchStatistics } = useLiquityDataFetching();
  const { resetProtocolStatsPriceQueryStatus } = useHistoricCachePriceStore();
  const { fetchPrices } = usePriceTaskManager();
  const currencySymbol = useSetting('currencySymbol');
  const premium = usePremium();

  async function fetch(refresh = false): Promise<void> {
    // The previous run's per-asset progress would otherwise be read as this run's.
    resetProtocolStatsPriceQueryStatus('liquity');

    await Promise.all([
      fetchStaking(refresh),
      fetchPools(refresh),
      fetchStatistics(refresh),
      fetchPrices({
        ignoreCache: refresh,
        selectedAssets: LIQUITY_PRICED_ASSETS,
      }),
    ]);
  }

  watchImmediate(moduleEnabled, async (enabled) => {
    if (enabled)
      await fetch();
  });

  // Every recorded value is denominated in the profit currency, so a change invalidates the cache.
  watch(currencySymbol, async () => {
    if (get(moduleEnabled))
      await fetch(true);
  });

  return {
    fetch,
    moduleEnabled,
    premium,
  };
}
