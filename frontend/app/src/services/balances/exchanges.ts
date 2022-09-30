import { ActionResult } from '@rotki/common/lib/data';
import { AxiosResponse } from 'axios';
import { axiosSnakeCaseTransformer } from '@/services/axios-tranformers';
import { basicAxiosTransformer } from '@/services/consts';
import { api } from '@/services/rotkehlchen-api';
import { PendingTask } from '@/services/types-api';
import {
  handleResponse,
  validStatus,
  validWithSessionStatus
} from '@/services/utils';
import { Exchange, ExchangePayload, Exchanges } from '@/types/exchanges';
import { nonNullProperties } from '@/utils/data';

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
    ignoreCache: boolean = false
  ): Promise<PendingTask> => {
    const response = await api.instance.get<ActionResult<PendingTask>>(
      `/exchanges/balances/${location}`,
      {
        params: axiosSnakeCaseTransformer({
          asyncQuery: true,
          ignoreCache: ignoreCache ? true : undefined
        }),
        validateStatus: validStatus,
        transformResponse: basicAxiosTransformer
      }
    );

    return handleResponse(response);
  };

  const querySetupExchange = async (
    payload: ExchangePayload,
    edit: Boolean
  ): Promise<boolean> => {
    let request: Promise<AxiosResponse<ActionResult<boolean>>>;

    if (!edit) {
      request = api.instance.put<ActionResult<boolean>>(
        '/exchanges',
        axiosSnakeCaseTransformer(nonNullProperties(payload)),
        {
          validateStatus: validStatus
        }
      );
    } else {
      request = api.instance.patch<ActionResult<boolean>>(
        '/exchanges',
        axiosSnakeCaseTransformer(nonNullProperties(payload)),
        {
          validateStatus: validStatus
        }
      );
    }

    return request.then(handleResponse);
  };

  const getExchanges = async (): Promise<Exchanges> => {
    const response = await api.instance.get<ActionResult<Exchanges>>(
      '/exchanges',
      {
        transformResponse: basicAxiosTransformer,
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
        params: axiosSnakeCaseTransformer({
          location: location
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
        params: axiosSnakeCaseTransformer({
          location: location
        })
      }
    );

    return handleResponse(response);
  };

  return {
    queryRemoveExchange,
    queryExchangeBalances,
    querySetupExchange,
    getExchanges,
    queryBinanceMarkets,
    queryBinanceUserMarkets
  };
};
