import type { AxiosResponse } from 'axios';
import type { PendingTask } from '@/types/task';
import { type ActionResult, transformCase } from '@rotki/common';
import { snakeCaseTransformer } from '@/services/axios-transformers';
import { api } from '@/services/rotkehlchen-api';
import {
  handleResponse,
  paramsSerializer,
  validStatus,
  validWithParamsSessionAndExternalService,
  validWithSessionStatus,
} from '@/services/utils';
import {
  type Exchange,
  type ExchangeFormData,
  Exchanges,
  ExchangeSavingsCollectionResponse,
  type ExchangeSavingsRequestPayload,
} from '@/types/exchanges';
import { nonEmptyProperties } from '@/utils/data';

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
  const queryRemoveExchange = async ({ location, name }: Exchange): Promise<boolean> => {
    const response = await api.instance.delete<ActionResult<boolean>>('/exchanges', {
      data: {
        location,
        name,
      },
      validateStatus: validStatus,
    });

    return handleResponse(response);
  };

  const queryExchangeBalances = async (location: string, ignoreCache = false, usdValueThreshold?: string): Promise<PendingTask> => {
    const response = await api.instance.get<ActionResult<PendingTask>>(`/exchanges/balances/${location}`, {
      params: snakeCaseTransformer({
        asyncQuery: true,
        ignoreCache: ignoreCache ? true : undefined,
        usdValueThreshold,
      }),
      validateStatus: validStatus,
    });

    return handleResponse(response);
  };

  const callSetupExchange = async ({ mode, ...payload }: ExchangeFormData): Promise<boolean> => {
    let response: AxiosResponse<ActionResult<boolean>>;

    const newPayload = {
      ...payload,
      okxLocation: payload.okxLocation ? payload.okxLocation.toLowerCase() : undefined,
    };

    if (mode === 'edit') {
      response = await api.instance.patch<ActionResult<boolean>>(
        '/exchanges',
        snakeCaseTransformer(nonEmptyProperties(newPayload, {
          alwaysPickKeys: ['binanceMarkets'],
          removeEmptyString: true,
        })),
        {
          validateStatus: validStatus,
        },
      );
    }
    else {
      response = await api.instance.put<ActionResult<boolean>>(
        '/exchanges',
        snakeCaseTransformer(nonEmptyProperties(newPayload, {
          removeEmptyString: true,
        })),
        {
          validateStatus: validStatus,
        },
      );
    }

    return handleResponse(response);
  };

  const getExchanges = async (): Promise<Exchanges> => {
    const response = await api.instance.get<ActionResult<Exchanges>>('/exchanges', {
      validateStatus: validWithSessionStatus,
    });

    const data = handleResponse(response);
    return Exchanges.parse(data);
  };

  const queryBinanceMarkets = async (location: string): Promise<string[]> => {
    const response = await api.instance.get<ActionResult<string[]>>('/exchanges/binance/pairs', {
      params: snakeCaseTransformer({
        location,
      }),
    });

    return handleResponse(response);
  };

  const queryBinanceUserMarkets = async (name: string, location: string): Promise<string[]> => {
    const response = await api.instance.get<ActionResult<string[]>>(`/exchanges/binance/pairs/${name}`, {
      params: snakeCaseTransformer({
        location,
      }),
    });

    return handleResponse(response);
  };

  const deleteExchangeData = async (name?: string): Promise<boolean> => {
    let url = `/exchanges/data`;
    if (name)
      url += `/${name}`;

    const response = await api.instance.delete<ActionResult<boolean>>(url, {
      validateStatus: validStatus,
    });

    return handleResponse(response);
  };

  const internalExchangeSavings = async <T>(
    payload: ExchangeSavingsRequestPayload,
    asyncQuery: boolean,
  ): Promise<T> => {
    const response = await api.instance.post<ActionResult<T>>(
      `/exchanges/${payload.location}/savings`,
      snakeCaseTransformer(
        nonEmptyProperties({
          asyncQuery,
          ...payload,
          orderByAttributes: payload.orderByAttributes?.map(item => transformCase(item)) ?? [],
        }),
      ),
      {
        paramsSerializer,
        validateStatus: validWithParamsSessionAndExternalService,
      },
    );

    return handleResponse(response);
  };

  const getExchangeSavingsTask = async (payload: ExchangeSavingsRequestPayload): Promise<PendingTask> =>
    internalExchangeSavings<PendingTask>(payload, true);

  const getExchangeSavings = async (
    payload: ExchangeSavingsRequestPayload,
  ): Promise<ExchangeSavingsCollectionResponse> => {
    const response = await internalExchangeSavings<ExchangeSavingsCollectionResponse>(payload, false);

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
