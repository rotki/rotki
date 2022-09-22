import { Blockchain } from '@rotki/common/lib/blockchain';
import { ActionResult } from '@rotki/common/lib/data';
import { axiosSnakeCaseTransformer } from '@/services/axios-tranformers';
import { basicAxiosTransformer } from '@/services/consts';
import { api } from '@/services/rotkehlchen-api';
import { PendingTask } from '@/services/types-api';
import {
  handleResponse,
  validWithParamsSessionAndExternalService,
  validWithSessionAndExternalService
} from '@/services/utils';

export const useBlockchainBalanceApi = () => {
  const queryLoopringBalances = async (): Promise<PendingTask> => {
    const response = await api.instance.get<ActionResult<PendingTask>>(
      'blockchains/ETH/modules/loopring/balances',
      {
        params: axiosSnakeCaseTransformer({ asyncQuery: true }),
        validateStatus: validWithSessionAndExternalService,
        transformResponse: basicAxiosTransformer
      }
    );
    return handleResponse(response);
  };

  async function queryBlockchainBalances(
    ignoreCache: boolean = false,
    blockchain?: Blockchain
  ): Promise<PendingTask> {
    let url = '/balances/blockchains';
    if (blockchain) {
      url += `/${blockchain}`;
    }
    const response = await api.instance.get<ActionResult<PendingTask>>(url, {
      params: axiosSnakeCaseTransformer({
        asyncQuery: true,
        ignoreCache: ignoreCache ? true : undefined
      }),
      validateStatus: validWithParamsSessionAndExternalService,
      transformResponse: basicAxiosTransformer
    });
    return handleResponse(response);
  }

  return {
    queryBlockchainBalances,
    queryLoopringBalances
  };
};
