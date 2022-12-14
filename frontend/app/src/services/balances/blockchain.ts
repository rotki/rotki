import { type Blockchain } from '@rotki/common/lib/blockchain';
import { type ActionResult } from '@rotki/common/lib/data';
import { type Nullable } from '@rotki/common';
import { axiosSnakeCaseTransformer } from '@/services/axios-tranformers';
import { api } from '@/services/rotkehlchen-api';
import { type PendingTask } from '@/services/types-api';
import {
  handleResponse,
  validStatus,
  validWithParamsSessionAndExternalService,
  validWithSessionAndExternalService
} from '@/services/utils';
import { EthDetectedTokensRecord } from '@/services/balances/types';
import { type Module } from '@/types/modules';

export const useBlockchainBalanceApi = () => {
  const queryLoopringBalances = async (): Promise<PendingTask> => {
    const response = await api.instance.get<ActionResult<PendingTask>>(
      'blockchains/ETH/modules/loopring/balances',
      {
        params: axiosSnakeCaseTransformer({ asyncQuery: true }),
        validateStatus: validWithSessionAndExternalService
      }
    );
    return handleResponse(response);
  };

  const queryBlockchainBalances = async (
    ignoreCache = false,
    blockchain?: Blockchain
  ): Promise<PendingTask> => {
    let url = '/balances/blockchains';
    if (blockchain) {
      url += `/${blockchain}`;
    }
    const response = await api.instance.get<ActionResult<PendingTask>>(url, {
      params: axiosSnakeCaseTransformer({
        asyncQuery: true,
        ignoreCache: ignoreCache ? true : undefined
      }),
      validateStatus: validWithParamsSessionAndExternalService
    });
    return handleResponse(response);
  };

  const internalDetectedTokens = async <T>(
    addresses: string[] | null,
    asyncQuery: boolean
  ): Promise<T> => {
    const response = await api.instance.post<ActionResult<T>>(
      '/blockchains/ETH/tokens/detect',
      axiosSnakeCaseTransformer({
        asyncQuery,
        onlyCache: !asyncQuery,
        addresses
      }),
      {
        validateStatus: validWithParamsSessionAndExternalService
      }
    );

    return handleResponse(response);
  };

  const fetchDetectedTokensTask = async (
    addresses: string[]
  ): Promise<PendingTask> => {
    return internalDetectedTokens<PendingTask>(addresses, true);
  };

  const fetchDetectedTokens = async (
    addresses: string[] | null
  ): Promise<EthDetectedTokensRecord> => {
    const response = await internalDetectedTokens<EthDetectedTokensRecord>(
      addresses,
      false
    );

    return EthDetectedTokensRecord.parse(response);
  };

  const deleteModuleData = async (
    module: Nullable<Module> = null
  ): Promise<boolean> => {
    const url = module
      ? `/blockchains/ETH/modules/${module}/data`
      : `/blockchains/ETH/modules/data`;
    const response = await api.instance.delete<ActionResult<boolean>>(url, {
      validateStatus: validStatus
    });

    return handleResponse(response);
  };

  return {
    queryBlockchainBalances,
    queryLoopringBalances,
    fetchDetectedTokens,
    fetchDetectedTokensTask,
    deleteModuleData
  };
};
