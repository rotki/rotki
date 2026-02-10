import type { ComputedRef, MaybeRef } from 'vue';
import { usePriceUtils } from '@/modules/prices/use-price-utils';
import { PriceOracle } from '@/types/settings/price-oracle';

export interface OracleInfoOptions {
  priceAsset: MaybeRef<string>;
  isAssetPrice: MaybeRef<boolean>;
}

export interface OracleInfoReturn {
  assetOracle: ComputedRef<string | undefined>;
  isManualPrice: ComputedRef<boolean>;
}

export function useOracleInfo(options: OracleInfoOptions): OracleInfoReturn {
  const { isAssetPrice, priceAsset } = options;

  const { t } = useI18n({ useScope: 'global' });
  const { getAssetPriceOracle, isManualAssetPrice } = usePriceUtils();

  const isManualPrice = computed<boolean>(() => {
    if (!get(isAssetPrice) || !get(priceAsset))
      return false;
    return get(isManualAssetPrice(priceAsset));
  });

  const assetOracle = computed<string | undefined>(() => {
    if (!get(isAssetPrice) || !get(priceAsset)) {
      return undefined;
    }

    const oracleKey = get(getAssetPriceOracle(priceAsset));
    const mapping: Record<string, string> = {
      [PriceOracle.MANUALCURRENT]: t('oracles.manual_current'),
      [PriceOracle.UNISWAP2]: t('oracles.uniswap_v2'),
      [PriceOracle.UNISWAP3]: t('oracles.uniswap_v3'),
    };

    return mapping[oracleKey] || oracleKey;
  });

  return {
    assetOracle,
    isManualPrice,
  };
}
