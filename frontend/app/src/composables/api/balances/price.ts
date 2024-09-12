import { snakeCaseTransformer } from '@/services/axios-tranformers';
import { api } from '@/services/rotkehlchen-api';
import {
  handleResponse,
  paramsSerializer,
  validStatus,
  validWithSessionAndExternalService,
  validWithoutSessionStatus,
} from '@/services/utils';
import type { ActionResult } from '@rotki/common';
import type { SupportedCurrency } from '@/types/currencies';
import type { PriceOracle } from '@/types/settings/price-oracle';
import type { HistoricPricesPayload, OracleCacheMeta } from '@/types/prices';
import type { PendingTask } from '@/types/task';

interface UsePriceApiReturn {
  queryPrices: (assets: string[], targetAsset: string, ignoreCache: boolean) => Promise<PendingTask>;
  queryFiatExchangeRates: (currencies: SupportedCurrency[]) => Promise<PendingTask>;
  queryHistoricalRate: (fromAsset: string, toAsset: string, timestamp: number) => Promise<PendingTask>;
  queryHistoricalRates: (payload: HistoricPricesPayload) => Promise<PendingTask>;
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
        purgeOld: purgeOld || undefined,
        fromAsset,
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
        asyncQuery: true,
        assetsTimestamp: [[fromAsset, timestamp]],
        targetAsset: toAsset,
      }),
      {
        validateStatus: validWithSessionAndExternalService,
      },
    );

    return handleResponse(response);
  };

  const queryHistoricalRates = async (payload: HistoricPricesPayload): Promise<PendingTask> => {
    const response = await api.instance.post<ActionResult<PendingTask>>(
      '/assets/prices/historical',
      snakeCaseTransformer({
        asyncQuery: true,
        ...payload,
      }),
      {
        validateStatus: validWithSessionAndExternalService,
      },
    );

    return handleResponse(response);
  };

  const queryPrices = async (assets: string[], targetAsset: string, ignoreCache: boolean): Promise<PendingTask> => {
    const response = await api.instance.post<ActionResult<PendingTask>>(
      '/assets/prices/latest',
      snakeCaseTransformer({
        asyncQuery: true,
        assets,
        targetAsset,
        ignoreCache: ignoreCache || undefined,
      }),
      {
        validateStatus: validWithSessionAndExternalService,
      },
    );

    return handleResponse(response);
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
    queryPrices,
    queryFiatExchangeRates,
    queryHistoricalRate,
    queryHistoricalRates,
    getPriceCache,
    createPriceCache,
    deletePriceCache,
  };
}
