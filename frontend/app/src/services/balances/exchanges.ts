import { type ActionResult } from '@rotki/common/lib/data';
import { type AxiosResponse } from 'axios';
import { axiosSnakeCaseTransformer } from '@/services/axios-tranformers';
import { api } from '@/services/rotkehlchen-api';
import { type PendingTask } from '@/services/types-api';
import {
  handleResponse,
  validStatus,
  validWithSessionStatus
} from '@/services/utils';
import {
  type Exchange,
  type ExchangePayload,
  Exchanges,
  type SupportedExchange
} from '@/types/exchanges';
import { nonEmptyProperties } from '@/utils/data';

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
        params: axiosSnakeCaseTransformer({
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
    edit: Boolean
  ): Promise<boolean> => {
    let response: AxiosResponse<ActionResult<boolean>>;

    if (!edit) {
      response = await api.instance.put<ActionResult<boolean>>(
        '/exchanges',
        axiosSnakeCaseTransformer(nonEmptyProperties(payload)),
        {
          validateStatus: validStatus
        }
      );
    } else {
      response = await api.instance.patch<ActionResult<boolean>>(
        '/exchanges',
        axiosSnakeCaseTransformer(nonEmptyProperties(payload)),
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
        params: axiosSnakeCaseTransformer({
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
        params: axiosSnakeCaseTransformer({
          location
        })
      }
    );

    return handleResponse(response);
  };

  const deleteExchangeData = async (
    name: SupportedExchange | '' = ''
  ): Promise<boolean> => {
    const response = await api.instance.delete<ActionResult<boolean>>(
      `/exchanges/data/${name}`,
      {
        validateStatus: validStatus
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
    queryBinanceUserMarkets,
    deleteExchangeData
  };
};
