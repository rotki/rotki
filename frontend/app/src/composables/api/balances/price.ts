import type { SupportedCurrency } from '@/types/currencies';
import type { PriceOracle } from '@/types/settings/price-oracle';
import { api } from '@/modules/api/rotki-api';
import {
  VALID_WITH_SESSION_AND_EXTERNAL_SERVICE,
  VALID_WITHOUT_SESSION_STATUS,
} from '@/modules/api/utils';
import { AssetPriceResponse, HistoricPrices, type HistoricPricesPayload, type OracleCacheMeta } from '@/types/prices';
import { type PendingTask, PendingTaskSchema } from '@/types/task';

interface UsePriceApiReturn {
  queryPrices: (assets: string[], targetAsset: string, ignoreCache: boolean) => Promise<PendingTask>;
  queryCachedPrices: (assets: string[], targetAsset: string) => Promise<AssetPriceResponse>;
  queryFiatExchangeRates: (currencies: SupportedCurrency[]) => Promise<PendingTask>;
  queryHistoricalRate: (fromAsset: string, toAsset: string, timestamp: number) => Promise<PendingTask>;
  queryHistoricalRates: (payload: HistoricPricesPayload) => Promise<PendingTask>;
  queryOnlyCacheHistoricalRates: (payload: Required<HistoricPricesPayload>) => Promise<HistoricPrices>;
  getPriceCache: (source: PriceOracle) => Promise<OracleCacheMeta[]>;
  createPriceCache: (source: PriceOracle, fromAsset: string, toAsset: string, purgeOld?: boolean) => Promise<PendingTask>;
  deletePriceCache: (source: PriceOracle, fromAsset: string, toAsset: string) => Promise<boolean>;
}

export function usePriceApi(): UsePriceApiReturn {
  const createPriceCache = async (
    source: PriceOracle,
    fromAsset: string,
    toAsset: string,
    purgeOld = false,
  ): Promise<PendingTask> => {
    const response = await api.post<PendingTask>(
      `/oracles/${source}/cache`,
      {
        asyncQuery: true,
        fromAsset,
        purgeOld: purgeOld || undefined,
        toAsset,
      },
      {
        validStatuses: VALID_WITH_SESSION_AND_EXTERNAL_SERVICE,
      },
    );
    return PendingTaskSchema.parse(response);
  };

  const deletePriceCache = async (source: PriceOracle, fromAsset: string, toAsset: string): Promise<boolean> => api.delete<boolean>(`/oracles/${source}/cache`, {
    body: {
      fromAsset,
      toAsset,
    },
  });

  const getPriceCache = async (source: PriceOracle): Promise<OracleCacheMeta[]> => api.get<OracleCacheMeta[]>(`/oracles/${source}/cache`, {
    validStatuses: VALID_WITH_SESSION_AND_EXTERNAL_SERVICE,
  });

  const queryHistoricalRate = async (fromAsset: string, toAsset: string, timestamp: number): Promise<PendingTask> => {
    const response = await api.post<PendingTask>(
      '/assets/prices/historical',
      {
        assetsTimestamp: [[fromAsset, timestamp]],
        asyncQuery: true,
        targetAsset: toAsset,
      },
      {
        validStatuses: VALID_WITH_SESSION_AND_EXTERNAL_SERVICE,
      },
    );
    return PendingTaskSchema.parse(response);
  };

  const queryHistoricalRates = async (payload: HistoricPricesPayload): Promise<PendingTask> => {
    const response = await api.post<PendingTask>(
      '/assets/prices/historical',
      {
        asyncQuery: true,
        ...payload,
      },
      {
        validStatuses: VALID_WITH_SESSION_AND_EXTERNAL_SERVICE,
      },
    );
    return PendingTaskSchema.parse(response);
  };

  const queryOnlyCacheHistoricalRates = async (payload: Required<HistoricPricesPayload>): Promise<HistoricPrices> => {
    const response = await api.post<HistoricPrices>(
      '/assets/prices/historical',
      payload,
      {
        validStatuses: VALID_WITH_SESSION_AND_EXTERNAL_SERVICE,
      },
    );
    return HistoricPrices.parse(response);
  };

  const queryPrices = async (assets: string[], targetAsset: string, ignoreCache: boolean): Promise<PendingTask> => {
    const response = await api.post<PendingTask>(
      '/assets/prices/latest',
      {
        assets,
        asyncQuery: true,
        ignoreCache: ignoreCache || undefined,
        targetAsset,
      },
      {
        validStatuses: VALID_WITH_SESSION_AND_EXTERNAL_SERVICE,
      },
    );
    return PendingTaskSchema.parse(response);
  };

  const queryCachedPrices = async (assets: string[], targetAsset: string): Promise<AssetPriceResponse> => {
    const response = await api.post<AssetPriceResponse>(
      '/assets/prices/latest',
      {
        assets,
        targetAsset,
      },
      {
        validStatuses: VALID_WITH_SESSION_AND_EXTERNAL_SERVICE,
      },
    );

    return AssetPriceResponse.parse(response);
  };

  const queryFiatExchangeRates = async (currencies: SupportedCurrency[]): Promise<PendingTask> => {
    const response = await api.get<PendingTask>('/exchange_rates', {
      query: {
        asyncQuery: true,
        currencies,
      },
      validStatuses: VALID_WITHOUT_SESSION_STATUS,
    });
    return PendingTaskSchema.parse(response);
  };

  return {
    createPriceCache,
    deletePriceCache,
    getPriceCache,
    queryCachedPrices,
    queryFiatExchangeRates,
    queryHistoricalRate,
    queryHistoricalRates,
    queryOnlyCacheHistoricalRates,
    queryPrices,
  };
}
