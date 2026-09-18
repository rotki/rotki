import type { ComputedRef } from 'vue';
import { useAssetPricesApi } from '@/modules/assets/api/use-asset-prices-api';
import { useAssetsStore } from '@/modules/assets/use-assets-store';
import { useBalancePricesStore } from '@/modules/balances/use-balance-prices-store';
import { logger } from '@/modules/core/common/logging/logging';

interface UseMissingPricesReturn {
  /** The assets missing a price that an oracle priced before, which are the ones worth fixing. */
  missingPriceIdentifiers: ComputedRef<string[]>;
  missingPricesCount: ComputedRef<number>;
}

/**
 * Counts the assets whose price is missing, but only those an oracle priced in the past.
 *
 * @remarks
 * An asset the oracles never supported is unsupported, not missing, so a standing zero for it is not
 * flagged; one that had an oracle price and now reports none is a genuine failure. Ignored assets are
 * hidden from the balances, so they do not count either. Whether an oracle ever priced an asset rarely
 * changes, so each asset is asked about once per session; a failed request is forgotten, letting a
 * later price tick ask again (colibri may still be starting). Shared, so the row and the dialog read
 * one cache.
 */
export const useMissingPrices = createSharedComposable((): UseMissingPricesReturn => {
  const { prices } = storeToRefs(useBalancePricesStore());
  const { isAssetIgnored } = useAssetsStore();
  const { assetsHadOraclePrice } = useAssetPricesApi();

  const oraclePriced = ref<Record<string, boolean>>({});
  const asked = new Set<string>();

  const unpricedVisibleAssets = computed<string[]>(() =>
    Object.entries(get(prices))
      .filter(([asset, price]) => price.priceMissing && !isAssetIgnored(asset))
      .map(([asset]) => asset),
  );

  const missingPriceIdentifiers = computed<string[]>(() => {
    const priced = get(oraclePriced);
    return get(unpricedVisibleAssets).filter(asset => priced[asset]);
  });

  const missingPricesCount = computed<number>(() => get(missingPriceIdentifiers).length);

  async function askOracles(assets: string[]): Promise<void> {
    const unasked = assets.filter(asset => !asked.has(asset));
    if (unasked.length === 0)
      return;

    unasked.forEach(asset => asked.add(asset));
    try {
      set(oraclePriced, { ...get(oraclePriced), ...await assetsHadOraclePrice(unasked) });
    }
    catch (error) {
      unasked.forEach(asset => asked.delete(asset));
      logger.error(error);
    }
  }

  watchImmediate(unpricedVisibleAssets, async assets => askOracles(assets));

  return {
    missingPriceIdentifiers,
    missingPricesCount,
  };
});
