import { transformCase } from '@rotki/common';
import { api } from '@/modules/api/rotki-api';
import {
  VALID_WITH_PARAMS_SESSION_AND_EXTERNAL_SERVICE,
  VALID_WITH_SESSION_STATUS,
} from '@/modules/api/utils';
import {
  type Exchange,
  type ExchangeFormData,
  Exchanges,
  ExchangeSavingsCollectionResponse,
  type ExchangeSavingsRequestPayload,
} from '@/types/exchanges';
import { type PendingTask, PendingTaskSchema } from '@/types/task';

interface UseExchangeApiReturn {
  queryRemoveExchange: ({ location, name }: Exchange) => Promise<boolean>;
  queryExchangeBalances: (location: string, ignoreCache?: boolean, usdValueThreshold?: string) => Promise<PendingTask>;
  callSetupExchange: (payload: ExchangeFormData) => Promise<boolean>;
  getExchanges: () => Promise<Exchanges>;
  queryBinanceMarkets: (location: string) => Promise<string[]>;
  queryBinanceUserMarkets: (name: string, location: string) => Promise<string[]>;
  deleteExchangeData: (name?: string) => Promise<boolean>;
  getExchangeSavingsTask: (payload: ExchangeSavingsRequestPayload) => Promise<PendingTask>;
  getExchangeSavings: (payload: ExchangeSavingsRequestPayload) => Promise<ExchangeSavingsCollectionResponse>;
}

export function useExchangeApi(): UseExchangeApiReturn {
  const queryRemoveExchange = async ({ location, name }: Exchange): Promise<boolean> => api.delete<boolean>('/exchanges', {
    body: {
      location,
      name,
    },
  });

  const queryExchangeBalances = async (location: string, ignoreCache = false, usdValueThreshold?: string): Promise<PendingTask> => {
    const response = await api.get<PendingTask>(`/exchanges/balances/${location}`, {
      query: {
        asyncQuery: true,
        ignoreCache: ignoreCache ? true : undefined,
        usdValueThreshold,
      },
    });
    return PendingTaskSchema.parse(response);
  };

  const callSetupExchange = async ({ mode, ...payload }: ExchangeFormData): Promise<boolean> => {
    if (mode === 'edit') {
      return api.patch<boolean>(
        '/exchanges',
        payload,
        {
          filterEmptyProperties: {
            alwaysPickKeys: ['binanceMarkets'],
            removeEmptyString: true,
          },
        },
      );
    }

    return api.put<boolean>(
      '/exchanges',
      payload,
      {
        filterEmptyProperties: {
          removeEmptyString: true,
        },
      },
    );
  };

  const getExchanges = async (): Promise<Exchanges> => {
    const data = await api.get<Exchanges>('/exchanges', {
      validStatuses: VALID_WITH_SESSION_STATUS,
    });

    return Exchanges.parse(data);
  };

  const queryBinanceMarkets = async (location: string): Promise<string[]> => api.get<string[]>('/exchanges/binance/pairs', {
    query: { location },
  });

  const queryBinanceUserMarkets = async (name: string, location: string): Promise<string[]> => api.get<string[]>(`/exchanges/binance/pairs/${name}`, {
    query: { location },
  });

  const deleteExchangeData = async (name?: string): Promise<boolean> => {
    let url = `/exchanges/data`;
    if (name)
      url += `/${name}`;

    return api.delete<boolean>(url);
  };

  const getExchangeSavingsTask = async (payload: ExchangeSavingsRequestPayload): Promise<PendingTask> => {
    const response = await api.post<PendingTask>(
      `/exchanges/${payload.location}/savings`,
      {
        asyncQuery: true,
        ...payload,
        orderByAttributes: payload.orderByAttributes?.map(item => transformCase(item)) ?? [],
      },
      {
        filterEmptyProperties: true,
        validStatuses: VALID_WITH_PARAMS_SESSION_AND_EXTERNAL_SERVICE,
      },
    );
    return PendingTaskSchema.parse(response);
  };

  const getExchangeSavings = async (
    payload: ExchangeSavingsRequestPayload,
  ): Promise<ExchangeSavingsCollectionResponse> => {
    const response = await api.post<ExchangeSavingsCollectionResponse>(
      `/exchanges/${payload.location}/savings`,
      {
        ...payload,
        orderByAttributes: payload.orderByAttributes?.map(item => transformCase(item)) ?? [],
      },
      {
        filterEmptyProperties: true,
        validStatuses: VALID_WITH_PARAMS_SESSION_AND_EXTERNAL_SERVICE,
      },
    );
    return ExchangeSavingsCollectionResponse.parse(response);
  };

  return {
    callSetupExchange,
    deleteExchangeData,
    getExchanges,
    getExchangeSavings,
    getExchangeSavingsTask,
    queryBinanceMarkets,
    queryBinanceUserMarkets,
    queryExchangeBalances,
    queryRemoveExchange,
  };
}
