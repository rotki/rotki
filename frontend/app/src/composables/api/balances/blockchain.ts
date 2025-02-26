import { snakeCaseTransformer } from '@/services/axios-transformers';
import { api } from '@/services/rotkehlchen-api';
import {
  handleResponse,
  validStatus,
  validWithParamsSessionAndExternalService,
  validWithSessionAndExternalService,
} from '@/services/utils';
import { EvmTokensRecord } from '@/types/balances';
import type { ActionResult, Nullable } from '@rotki/common';
import type { PendingTask } from '@/types/task';
import type { PurgeableModule } from '@/types/modules';

interface UseBlockchainBalancesApiReturn {
  queryBlockchainBalances: (ignoreCache?: boolean, blockchain?: string, usdValueThreshold?: string) => Promise<PendingTask>;
  queryLoopringBalances: () => Promise<PendingTask>;
  fetchDetectedTokens: (chain: string, addresses: string[] | null) => Promise<EvmTokensRecord>;
  fetchDetectedTokensTask: (chain: string, addresses: string[]) => Promise<PendingTask>;
  deleteModuleData: (module?: Nullable<PurgeableModule>) => Promise<boolean>;
}

export function useBlockchainBalancesApi(): UseBlockchainBalancesApiReturn {
  const queryLoopringBalances = async (): Promise<PendingTask> => {
    const response = await api.instance.get<ActionResult<PendingTask>>('blockchains/eth/modules/loopring/balances', {
      params: snakeCaseTransformer({ asyncQuery: true }),
      validateStatus: validWithSessionAndExternalService,
    });
    return handleResponse(response);
  };

  const queryBlockchainBalances = async (ignoreCache = false, blockchain?: string, usdValueThreshold?: string): Promise<PendingTask> => {
    let url = '/balances/blockchains';
    if (blockchain)
      url += `/${blockchain}`;

    const response = await api.instance.get<ActionResult<PendingTask>>(url, {
      params: snakeCaseTransformer({
        asyncQuery: true,
        ignoreCache: ignoreCache ? true : undefined,
        usdValueThreshold,
      }),
      validateStatus: validWithParamsSessionAndExternalService,
    });
    return handleResponse(response);
  };

  const internalDetectedTokens = async <T>(
    chain: string,
    addresses: string[] | null,
    asyncQuery: boolean,
  ): Promise<T> => {
    const response = await api.instance.post<ActionResult<T>>(
      `/blockchains/${chain}/tokens/detect`,
      snakeCaseTransformer({
        addresses,
        asyncQuery,
        onlyCache: !asyncQuery,
      }),
      {
        validateStatus: validWithParamsSessionAndExternalService,
      },
    );

    return handleResponse(response);
  };

  const fetchDetectedTokensTask = async (chain: string, addresses: string[]): Promise<PendingTask> =>
    internalDetectedTokens<PendingTask>(chain, addresses, true);

  const fetchDetectedTokens = async (chain: string, addresses: string[] | null): Promise<EvmTokensRecord> => {
    const response = await internalDetectedTokens<EvmTokensRecord>(chain, addresses, false);

    return EvmTokensRecord.parse(response);
  };

  const deleteModuleData = async (module: Nullable<PurgeableModule> = null): Promise<boolean> => {
    const url = module ? `/blockchains/eth/modules/${module}/data` : `/blockchains/eth/modules/data`;
    const response = await api.instance.delete<ActionResult<boolean>>(url, {
      validateStatus: validStatus,
    });

    return handleResponse(response);
  };

  return {
    deleteModuleData,
    fetchDetectedTokens,
    fetchDetectedTokensTask,
    queryBlockchainBalances,
    queryLoopringBalances,
  };
}
