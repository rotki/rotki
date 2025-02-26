import { snakeCaseTransformer } from '@/services/axios-transformers';
import { api } from '@/services/rotkehlchen-api';
import {
  handleResponse,
  paramsSerializer,
  validStatus,
  validWithSessionAndExternalService,
  validWithoutSessionStatus,
} from '@/services/utils';
import { AssetPriceResponse, HistoricPrices, type HistoricPricesPayload, type OracleCacheMeta } from '@/types/prices';
import type { ActionResult } from '@rotki/common';
import type { SupportedCurrency } from '@/types/currencies';
import type { PriceOracle } from '@/types/settings/price-oracle';
import type { PendingTask } from '@/types/task';

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
    const response = await api.instance.post<ActionResult<PendingTask>>(
      `/oracles/${source}/cache`,
      snakeCaseTransformer({
        asyncQuery: true,
        fromAsset,
        purgeOld: purgeOld || undefined,
        toAsset,
      }),
      {
        validateStatus: validWithSessionAndExternalService,
      },
    );

    return handleResponse(response);
  };

  const deletePriceCache = async (source: PriceOracle, fromAsset: string, toAsset: string): Promise<boolean> => {
    const response = await api.instance.delete<ActionResult<boolean>>(`/oracles/${source}/cache`, {
      data: snakeCaseTransformer({
        fromAsset,
        toAsset,
      }),
      validateStatus: validStatus,
    });

    return handleResponse(response);
  };

  const getPriceCache = async (source: PriceOracle): Promise<OracleCacheMeta[]> => {
    const response = await api.instance.get<ActionResult<OracleCacheMeta[]>>(`/oracles/${source}/cache`, {
      validateStatus: validWithSessionAndExternalService,
    });

    return handleResponse(response);
  };

  const queryHistoricalRate = async (fromAsset: string, toAsset: string, timestamp: number): Promise<PendingTask> => {
    const response = await api.instance.post<ActionResult<PendingTask>>(
      '/assets/prices/historical',
      snakeCaseTransformer({
        assetsTimestamp: [[fromAsset, timestamp]],
        asyncQuery: true,
        targetAsset: toAsset,
      }),
      {
        validateStatus: validWithSessionAndExternalService,
      },
    );

    return handleResponse(response);
  };

  const internalQueryHistoricalRates = async <T>(
    payload: HistoricPricesPayload,
  ): Promise<T> => {
    const response = await api.instance.post<ActionResult<T>>(
      '/assets/prices/historical',
      snakeCaseTransformer({
        asyncQuery: !payload.onlyCachePeriod,
        ...payload,
      }),
      {
        validateStatus: validWithSessionAndExternalService,
      },
    );

    return handleResponse(response);
  };

  const queryHistoricalRates = async (payload: HistoricPricesPayload): Promise<PendingTask> => internalQueryHistoricalRates<PendingTask>(payload);

  const queryOnlyCacheHistoricalRates = async (payload: Required<HistoricPricesPayload>): Promise<HistoricPrices> => {
    const response = await internalQueryHistoricalRates<HistoricPrices>(payload);
    return HistoricPrices.parse(response);
  };

  const queryPrices = async (assets: string[], targetAsset: string, ignoreCache: boolean): Promise<PendingTask> => {
    const response = await api.instance.post<ActionResult<PendingTask>>(
      '/assets/prices/latest',
      snakeCaseTransformer({
        assets,
        asyncQuery: true,
        ignoreCache: ignoreCache || undefined,
        targetAsset,
      }),
      {
        validateStatus: validWithSessionAndExternalService,
      },
    );

    return handleResponse(response);
  };

  const queryCachedPrices = async (assets: string[], targetAsset: string): Promise<AssetPriceResponse> => {
    const response = await api.instance.post<ActionResult<AssetPriceResponse>>(
      '/assets/prices/latest',
      snakeCaseTransformer({
        assets,
        asyncQuery: false,
        ignoreCache: false,
        targetAsset,
      }),
      {
        validateStatus: validWithSessionAndExternalService,
      },
    );

    return AssetPriceResponse.parse(handleResponse(response));
  };

  const queryFiatExchangeRates = async (currencies: SupportedCurrency[]): Promise<PendingTask> => {
    const response = await api.instance.get<ActionResult<PendingTask>>('/exchange_rates', {
      params: {
        async_query: true,
        currencies,
      },
      paramsSerializer,
      validateStatus: validWithoutSessionStatus,
    });

    return handleResponse(response);
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
