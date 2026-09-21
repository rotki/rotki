import { transformCase } from '@rotki/common';
import {
  type Exchange,
  type ExchangeConnector,
  ExchangeConnectors,
  type ExchangeFormData,
  Exchanges,
  ExchangeSavingsCollectionResponse,
  type ExchangeSavingsRequestPayload,
} from '@/modules/balances/types/exchanges';
import { api } from '@/modules/core/api/rotki-api';
import {
  VALID_WITH_PARAMS_SESSION_AND_EXTERNAL_SERVICE,
  VALID_WITH_SESSION_STATUS,
} from '@/modules/core/api/utils';
import { type PendingTask, PendingTaskSchema } from '@/modules/core/tasks/types';

export interface UseExchangeApiReturn {
  queryRemoveExchange: ({ identifier }: Exchange) => Promise<boolean>;
  queryExchangeBalances: (location: string, ignoreCache?: boolean, valueThreshold?: string) => Promise<PendingTask>;
  callSetupExchange: (payload: ExchangeFormData) => Promise<boolean>;
  getExchanges: () => Promise<Exchanges>;
  getSupportedExchanges: () => Promise<ExchangeConnector[]>;
  queryBinanceHistoryStartTimestamp: () => Promise<number>;
  queryBinanceMarkets: (location: string) => Promise<string[]>;
  queryBinanceUserMarkets: (identifier: string) => Promise<string[]>;
  deleteExchangeData: (
    name?: string,
    dataType?: 'all' | 'trades' | 'asset_movements' | 'other',
  ) => Promise<boolean>;
  getExchangeSavingsTask: (payload: ExchangeSavingsRequestPayload) => Promise<PendingTask>;
  getExchangeSavings: (payload: ExchangeSavingsRequestPayload) => Promise<ExchangeSavingsCollectionResponse>;
}

export function useExchangeApi(): UseExchangeApiReturn {
  type ExchangePurgeType = 'all' | 'trades' | 'asset_movements' | 'other';

  const queryRemoveExchange = async ({ identifier }: Exchange): Promise<boolean> => api.delete<boolean>('/exchanges', {
    body: { identifier },
  });

  const queryExchangeBalances = async (location: string, ignoreCache = false, valueThreshold?: string): Promise<PendingTask> => {
    const response = await api.get<PendingTask>(`/exchanges/balances/${location}`, {
      query: {
        asyncQuery: true,
        ignoreCache: ignoreCache ? true : undefined,
        valueThreshold,
      },
    });
    return PendingTaskSchema.parse(response);
  };

  /**
   * Adds a connection for the connector in `location`, or edits the connection `identifier`.
   * Name and connector identify nothing once a connection exists, so an edit only sends its
   * identifier.
   */
  const callSetupExchange = async ({ identifier, location, mode, name, ...payload }: ExchangeFormData): Promise<boolean> => {
    if (mode === 'edit') {
      return api.patch<boolean>(
        '/exchanges',
        { ...payload, identifier },
        {
          filterEmptyProperties: {
            alwaysPickKeys: ['binanceMarkets'],
            removeEmptyString: true,
          },
        },
      );
    }

    await api.put<{ identifier: string }>(
      '/exchanges',
      { ...payload, connector: location, name },
      {
        filterEmptyProperties: {
          removeEmptyString: true,
        },
      },
    );
    return true;
  };

  const getSupportedExchanges = async (): Promise<ExchangeConnector[]> =>
    ExchangeConnectors.parse(await api.get<ExchangeConnector[]>('/exchanges/supported'));

  const getExchanges = async (): Promise<Exchanges> => {
    const data = await api.get<Exchanges>('/exchanges', {
      validStatuses: VALID_WITH_SESSION_STATUS,
    });

    return Exchanges.parse(data);
  };

  const queryBinanceMarkets = async (location: string): Promise<string[]> => api.get<string[]>('/exchanges/binance/pairs', {
    query: { location },
  });

  const queryBinanceHistoryStartTimestamp = async (): Promise<number> =>
    api.get<number>('/exchanges/binance/history-start');

  const queryBinanceUserMarkets = async (identifier: string): Promise<string[]> =>
    api.get<string[]>(`/exchanges/binance/pairs/${encodeURIComponent(identifier)}`);

  const deleteExchangeData = async (name?: string, dataType: ExchangePurgeType = 'all'): Promise<boolean> => {
    let url = `/exchanges/data`;
    if (name)
      url += `/${name}`;

    return api.delete<boolean>(url, {
      query: dataType === 'all' ? undefined : { dataType },
    });
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
    getSupportedExchanges,
    getExchangeSavingsTask,
    queryBinanceHistoryStartTimestamp,
    queryBinanceMarkets,
    queryBinanceUserMarkets,
    queryExchangeBalances,
    queryRemoveExchange,
  };
}
