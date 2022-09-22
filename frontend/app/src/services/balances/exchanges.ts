import { ActionResult } from '@rotki/common/lib/data';
import { AxiosResponse } from 'axios';
import { axiosSnakeCaseTransformer } from '@/services/axios-tranformers';
import { basicAxiosTransformer } from '@/services/consts';
import { api } from '@/services/rotkehlchen-api';
import { PendingTask } from '@/services/types-api';
import { handleResponse, validStatus } from '@/services/utils';
import { Exchange, ExchangePayload } from '@/types/exchanges';
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

  return {
    queryRemoveExchange,
    queryExchangeBalances,
    querySetupExchange
  };
};
