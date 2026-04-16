import type { ComputedRef, MaybeRefOrGetter } from 'vue';
import { usePriceUtils } from '@/modules/assets/prices/use-price-utils';
import { PriceOracle } from '@/modules/settings/types/price-oracle';
import { useGeneralSettingsStore } from '@/modules/settings/use-general-settings-store';

export interface OracleInfoOptions {
  priceAsset: MaybeRefOrGetter<string>;
  isAssetPrice: MaybeRefOrGetter<boolean>;
}

export interface OracleInfoReturn {
  assetOracle: ComputedRef<string | undefined>;
  isManualPrice: ComputedRef<boolean>;
}

export function useOracleInfo(options: OracleInfoOptions): OracleInfoReturn {
  const { isAssetPrice, priceAsset } = options;

  const { t } = useI18n({ useScope: 'global' });
  const { getAssetPriceOracle, isManualAssetPrice } = usePriceUtils();
  const { currencySymbol } = storeToRefs(useGeneralSettingsStore());

  const isSameAsMainCurrency = computed<boolean>(() => toValue(priceAsset) === get(currencySymbol));

  const isManualPrice = computed<boolean>(() => {
    if (!toValue(isAssetPrice) || !toValue(priceAsset) || get(isSameAsMainCurrency))
      return false;
    return isManualAssetPrice(toValue(priceAsset));
  });

  const assetOracle = computed<string | undefined>(() => {
    if (!toValue(isAssetPrice) || !toValue(priceAsset) || get(isSameAsMainCurrency)) {
      return undefined;
    }

    const oracleKey = getAssetPriceOracle(toValue(priceAsset));
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
