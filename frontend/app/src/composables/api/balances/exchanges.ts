import { type ActionResult } from '@rotki/common/lib/data';
import { type AxiosResponse } from 'axios';
import { snakeCaseTransformer } from '@/services/axios-tranformers';
import { api } from '@/services/rotkehlchen-api';
import {
  handleResponse,
  paramsSerializer,
  validStatus,
  validWithParamsSessionAndExternalService,
  validWithSessionStatus
} from '@/services/utils';
import {
  type Exchange,
  type ExchangePayload,
  ExchangeSavingsCollectionResponse,
  type ExchangeSavingsRequestPayload,
  Exchanges
} from '@/types/exchanges';
import { type PendingTask } from '@/types/task';

export const useExchangeApi = () => {
  const queryRemoveExchange = async ({
    location,
    name
  }: Exchange): Promise<boolean> => {
    const response = await api.instance.delete<ActionResult<boolean>>(
      '/exchanges',
      {
        data: {
          name,
          location
        },
        validateStatus: validStatus
      }
    );

    return handleResponse(response);
  };

  const queryExchangeBalances = async (
    location: string,
    ignoreCache = false
  ): Promise<PendingTask> => {
    const response = await api.instance.get<ActionResult<PendingTask>>(
      `/exchanges/balances/${location}`,
      {
        params: snakeCaseTransformer({
          asyncQuery: true,
          ignoreCache: ignoreCache ? true : undefined
        }),
        validateStatus: validStatus
      }
    );

    return handleResponse(response);
  };

  const querySetupExchange = async (
    payload: ExchangePayload,
    edit: boolean
  ): Promise<boolean> => {
    let response: AxiosResponse<ActionResult<boolean>>;

    if (!edit) {
      response = await api.instance.put<ActionResult<boolean>>(
        '/exchanges',
        snakeCaseTransformer(nonEmptyProperties(payload)),
        {
          validateStatus: validStatus
        }
      );
    } else {
      response = await api.instance.patch<ActionResult<boolean>>(
        '/exchanges',
        snakeCaseTransformer(nonEmptyProperties(payload)),
        {
          validateStatus: validStatus
        }
      );
    }

    return handleResponse(response);
  };

  const getExchanges = async (): Promise<Exchanges> => {
    const response = await api.instance.get<ActionResult<Exchanges>>(
      '/exchanges',
      {
        validateStatus: validWithSessionStatus
      }
    );

    const data = handleResponse(response);
    return Exchanges.parse(data);
  };

  const queryBinanceMarkets = async (location: string): Promise<string[]> => {
    const response = await api.instance.get<ActionResult<string[]>>(
      '/exchanges/binance/pairs',
      {
        params: snakeCaseTransformer({
          location
        })
      }
    );

    return handleResponse(response);
  };

  const queryBinanceUserMarkets = async (
    name: string,
    location: string
  ): Promise<string[]> => {
    const response = await api.instance.get<ActionResult<string[]>>(
      `/exchanges/binance/pairs/${name}`,
      {
        params: snakeCaseTransformer({
          location
        })
      }
    );

    return handleResponse(response);
  };

  const deleteExchangeData = async (name?: string): Promise<boolean> => {
    let url = `/exchanges/data`;
    if (name) {
      url += `/${name}`;
    }
    const response = await api.instance.delete<ActionResult<boolean>>(url, {
      validateStatus: validStatus
    });

    return handleResponse(response);
  };

  const internalExchangeSavings = async <T>(
    payload: ExchangeSavingsRequestPayload,
    asyncQuery: boolean
  ): Promise<T> => {
    const response = await api.instance.post<ActionResult<T>>(
      `/exchanges/${payload.location}/savings`,
      snakeCaseTransformer(
        nonEmptyProperties({
          asyncQuery,
          ...payload,
          orderByAttributes:
            payload.orderByAttributes?.map(item => transformCase(item)) ?? []
        })
      ),
      {
        paramsSerializer,
        validateStatus: validWithParamsSessionAndExternalService
      }
    );

    return handleResponse(response);
  };

  const getExchangeSavingsTask = async (
    payload: ExchangeSavingsRequestPayload
  ): Promise<PendingTask> =>
    internalExchangeSavings<PendingTask>(payload, true);

  const getExchangeSavings = async (
    payload: ExchangeSavingsRequestPayload
  ): Promise<ExchangeSavingsCollectionResponse> => {
    const response =
      await internalExchangeSavings<ExchangeSavingsCollectionResponse>(
        payload,
        false
      );

    return ExchangeSavingsCollectionResponse.parse(response);
  };

  return {
    queryRemoveExchange,
    queryExchangeBalances,
    querySetupExchange,
    getExchanges,
    queryBinanceMarkets,
    queryBinanceUserMarkets,
    deleteExchangeData,
    getExchangeSavingsTask,
    getExchangeSavings
  };
};
