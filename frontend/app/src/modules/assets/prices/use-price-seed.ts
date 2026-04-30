import type { AssetPrices } from '@/modules/assets/prices/price-types';
import { usePriceRefresh } from '@/modules/assets/prices/use-price-refresh';
import { usePriceApi } from '@/modules/balances/api/use-price-api';
import { useBalancePricesStore } from '@/modules/balances/use-balance-prices-store';
import { useBalancesStore } from '@/modules/balances/use-balances-store';
import { useBlockchainRefreshTimestampsStore } from '@/modules/balances/use-blockchain-refresh-timestamps-store';
import { logger } from '@/modules/core/common/logging/logging';
import { useGeneralSettingsStore } from '@/modules/settings/use-general-settings-store';

const SEED_CACHE_WINDOW_SECONDS = 6 * 60 * 60;

interface UsePriceSeedReturn {
  seedFromHistoric: () => Promise<void>;
}

export function usePriceSeed(): UsePriceSeedReturn {
  const { queryOnlyCacheHistoricalRates } = usePriceApi();
  const { prices } = storeToRefs(useBalancePricesStore());
  const { balances } = storeToRefs(useBalancesStore());
  const { refreshTimestamps } = storeToRefs(useBlockchainRefreshTimestampsStore());
  const { currencySymbol } = storeToRefs(useGeneralSettingsStore());
  const { adjustPrices } = usePriceRefresh();

  const collectAssetsByNewestTimestamp = (): Map<string, number> => {
    const newestPerAsset = new Map<string, number>();
    const tsMap = get(refreshTimestamps);
    const blockchainBalances = get(balances);

    for (const [chain, ts] of Object.entries(tsMap)) {
      const accounts = blockchainBalances[chain];
      if (!accounts || ts <= 0)
        continue;

      for (const account in accounts) {
        const { assets, liabilities } = accounts[account];
        const assetIds = [...Object.keys(assets ?? {}), ...Object.keys(liabilities ?? {})];
        for (const asset of assetIds) {
          const previous = newestPerAsset.get(asset) ?? 0;
          if (ts > previous)
            newestPerAsset.set(asset, ts);
        }
      }
    }

    return newestPerAsset;
  };

  const seedFromHistoric = async (): Promise<void> => {
    const start = performance.now();
    const newestPerAsset = collectAssetsByNewestTimestamp();

    if (newestPerAsset.size === 0) {
      logger.debug('[price-seed] skipped — no chain timestamps or balances available');
      return;
    }

    const requested = newestPerAsset.size;
    logger.debug(`[price-seed] querying cached historic prices for ${requested} asset(s) (window ±${SEED_CACHE_WINDOW_SECONDS}s, target=${get(currencySymbol)})`);

    try {
      const result = await queryOnlyCacheHistoricalRates({
        assetsTimestamp: [...newestPerAsset.entries()].map(([asset, ts]) => [asset, String(ts)]),
        onlyCachePeriod: SEED_CACHE_WINDOW_SECONDS,
        targetAsset: get(currencySymbol),
      });

      const seeded: AssetPrices = {};
      for (const [asset, byTs] of Object.entries(result.assets ?? {})) {
        const value = Object.values(byTs ?? {})[0];
        if (value)
          seeded[asset] = { isManualPrice: false, oracle: '', value };
      }

      const seededCount = Object.keys(seeded).length;
      const elapsed = Math.round(performance.now() - start);

      if (seededCount === 0) {
        logger.debug(`[price-seed] no cached prices found for ${requested} asset(s) in ${elapsed}ms`);
        return;
      }

      set(prices, { ...get(prices), ...seeded });
      adjustPrices(seeded);
      logger.info(`[price-seed] seeded ${seededCount}/${requested} asset prices from cache in ${elapsed}ms`);
    }
    catch (error) {
      const elapsed = Math.round(performance.now() - start);
      logger.warn(`[price-seed] failed after ${elapsed}ms`, error);
    }
  };

  return { seedFromHistoric };
}
