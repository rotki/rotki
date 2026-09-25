import type { ResultAsync } from 'plainfp/result-async';
import type { MaybeRef } from 'vue';
import type { OraclePriceEntry, OraclePricesQuery } from '@/modules/assets/prices/price-types';
import type { Collection } from '@/modules/core/common/collection';
import { useAssetPricesApi } from '@/modules/assets/api/use-asset-prices-api';
import { useHistoricPriceCache } from '@/modules/assets/prices/use-historic-price-cache';
import { isRequestCancellation } from '@/modules/core/api/request-queue/is-request-cancellation';
import { fromRequest, type RequestError } from '@/modules/core/api/request-result';
import { getErrorMessage } from '@/modules/core/common/logging/error-handling';
import { useNotifications } from '@/modules/core/notifications/use-notifications';

interface UseOraclePricesReturn {
  deletePrice: (item: OraclePriceEntry) => Promise<boolean>;
  fetchData: (payload: MaybeRef<OraclePricesQuery>) => ResultAsync<Collection<OraclePriceEntry>, RequestError>;
}

export function useOraclePrices(): UseOraclePricesReturn {
  const { t } = useI18n({ useScope: 'global' });

  const { deleteHistoricalPrice, fetchOraclePrices } = useAssetPricesApi();
  const { resetHistoricalPricesData } = useHistoricPriceCache();
  const { notifyError } = useNotifications();

  const fetchData = async (
    payload: MaybeRef<OraclePricesQuery>,
  ): ResultAsync<Collection<OraclePriceEntry>, RequestError> =>
    fromRequest(async () => fetchOraclePrices(get(payload)));

  const deletePrice = async (item: OraclePriceEntry): Promise<boolean> => {
    try {
      await deleteHistoricalPrice({
        fromAsset: item.fromAsset,
        sourceType: item.sourceType,
        timestamp: item.timestamp,
        toAsset: item.toAsset,
      });
      resetHistoricalPricesData([{ fromAsset: item.fromAsset, timestamp: item.timestamp }]);
      return true;
    }
    catch (error: unknown) {
      if (isRequestCancellation(error))
        return false;

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
