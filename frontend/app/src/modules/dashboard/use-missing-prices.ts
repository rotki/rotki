import type { ComputedRef } from 'vue';
import { useAssetPricesApi } from '@/modules/assets/api/use-asset-prices-api';
import { useAssetsStore } from '@/modules/assets/use-assets-store';
import { useBalancePricesStore } from '@/modules/balances/use-balance-prices-store';
import { logger } from '@/modules/core/common/logging/logging';

interface UseMissingPricesReturn {
  missingPriceIdentifiers: ComputedRef<string[]>;
  missingPricesCount: ComputedRef<number>;
}

/**
 * Counts assets whose price is currently missing, but only those an oracle priced in
 * the past. An asset the oracles never supported is "unsupported", not "missing", so a
 * standing zero for it should not be flagged. Assets that once had an oracle price and
 * now report zero are genuine failures (the oracle broke) and are what we count.
 */
export function useMissingPrices(): UseMissingPricesReturn {
  const { prices } = storeToRefs(useBalancePricesStore());
  const { isAssetIgnored } = useAssetsStore();
  const { assetsHadOraclePrice } = useAssetPricesApi();

  // Cache of asset id -> whether an oracle ever recorded a price. Oracle support rarely
  // changes, so results are kept across price ticks; only unseen assets are queried.
  const oraclePriceHistory = ref<Record<string, boolean>>({});
  // Assets already queried (resolved or in-flight), so overlapping ticks don't re-fetch.
  const requested = new Set<string>();

  // Zero-priced assets the user can actually see. Ignored assets (spam/dust) are hidden
  // from the balances table, so they must not inflate the count either.
  const missingPriceAssets = computed<string[]>(() =>
    Object.entries(get(prices))
      .filter(([asset, price]) => price.priceMissing && !isAssetIgnored(asset))
      .map(([asset]) => asset),
  );

  // The assets that are genuinely missing a price: visible, zero-priced, and priced by an
  // oracle at least once before. These are the ones worth surfacing and fixing.
  const missingPriceIdentifiers = computed<string[]>(() => {
    const history = get(oraclePriceHistory);
    return get(missingPriceAssets).filter(asset => history[asset]);
  });

  const missingPricesCount = computed<number>(() => get(missingPriceIdentifiers).length);

  watchImmediate(missingPriceAssets, async (assets) => {
    const unknown = assets.filter(asset => !requested.has(asset));
    if (unknown.length === 0)
      return;

    unknown.forEach(asset => requested.add(asset));
    try {
      const existence = await assetsHadOraclePrice(unknown);
      set(oraclePriceHistory, { ...get(oraclePriceHistory), ...existence });
    }
    catch (error) {
      // Allow a later retry (e.g. colibri still starting) by forgetting these ids.
      unknown.forEach(asset => requested.delete(asset));
      logger.error(error);
    }
  });

  return {
    missingPriceIdentifiers,
    missingPricesCount,
  };
}
