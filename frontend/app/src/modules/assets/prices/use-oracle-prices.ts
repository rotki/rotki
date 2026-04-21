import type { MaybeRef } from 'vue';
import type { OraclePriceEntry, OraclePricesQuery } from '@/modules/assets/prices/price-types';
import type { Collection } from '@/modules/core/common/collection';
import { useAssetPricesApi } from '@/modules/assets/api/use-asset-prices-api';
import { defaultCollectionState } from '@/modules/core/common/data/collection-utils';
import { getErrorMessage } from '@/modules/core/common/logging/error-handling';
import { useNotifications } from '@/modules/core/notifications/use-notifications';

interface UseOraclePricesReturn {
  deletePrice: (item: OraclePriceEntry) => Promise<boolean>;
  fetchData: (payload: MaybeRef<OraclePricesQuery>) => Promise<Collection<OraclePriceEntry>>;
}

export function useOraclePrices(): UseOraclePricesReturn {
  const { t } = useI18n({ useScope: 'global' });

  const { deleteHistoricalPrice, fetchOraclePrices } = useAssetPricesApi();
  const { notifyError } = useNotifications();

  const fetchData = async (
    payload: MaybeRef<OraclePricesQuery>,
  ): Promise<Collection<OraclePriceEntry>> => {
    try {
      return await fetchOraclePrices(get(payload));
    }
    catch (error: unknown) {
      notifyError(
        t('oracle_prices.fetch.failure.title'),
        t('oracle_prices.fetch.failure.message', { message: getErrorMessage(error) }),
      );
      return defaultCollectionState<OraclePriceEntry>();
    }
  };

  const deletePrice = async (item: OraclePriceEntry): Promise<boolean> => {
    try {
      await deleteHistoricalPrice({
        fromAsset: item.fromAsset,
        sourceType: item.sourceType,
        timestamp: item.timestamp,
        toAsset: item.toAsset,
      });
      return true;
    }
    catch (error: unknown) {
      notifyError(
        t('oracle_prices.delete.failure.title'),
        t('oracle_prices.delete.failure.message', { message: getErrorMessage(error) }),
      );
      return false;
    }
  };

  return {
    deletePrice,
    fetchData,
  };
}
