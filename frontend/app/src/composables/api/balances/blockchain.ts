import type { Nullable } from '@rotki/common';
import type { FetchBlockchainBalancePayload } from '@/types/blockchain/balances';
import type { PurgeableModule } from '@/types/modules';
import { api } from '@/modules/api/rotki-api';
import {
  VALID_WITH_PARAMS_SESSION_AND_EXTERNAL_SERVICE,
  VALID_WITH_SESSION_AND_EXTERNAL_SERVICE,
} from '@/modules/api/utils';
import { EvmTokensRecord } from '@/types/balances';
import { type PendingTask, PendingTaskSchema } from '@/types/task';

interface UseBlockchainBalancesApiReturn {
  queryBlockchainBalances: (payload: FetchBlockchainBalancePayload, valueThreshold?: string) => Promise<PendingTask>;
  queryXpubBalances: (payload: FetchBlockchainBalancePayload) => Promise<PendingTask>;
  queryLoopringBalances: () => Promise<PendingTask>;
  fetchDetectedTokens: (chain: string, addresses: string[] | null) => Promise<EvmTokensRecord>;
  fetchDetectedTokensTask: (chain: string, addresses: string[]) => Promise<PendingTask>;
  deleteModuleData: (module?: Nullable<PurgeableModule>) => Promise<boolean>;
}

export function useBlockchainBalancesApi(): UseBlockchainBalancesApiReturn {
  const queryLoopringBalances = async (): Promise<PendingTask> => {
    const response = await api.get<PendingTask>('blockchains/eth/modules/loopring/balances', {
      query: { asyncQuery: true },
      validStatuses: VALID_WITH_SESSION_AND_EXTERNAL_SERVICE,
    });
    return PendingTaskSchema.parse(response);
  };

  const queryBlockchainBalances = async ({ addresses, blockchain, ignoreCache }: FetchBlockchainBalancePayload, valueThreshold?: string): Promise<PendingTask> => {
    let url = '/balances/blockchains';
    if (blockchain)
      url += `/${blockchain}`;

    const response = await api.get<PendingTask>(url, {
      query: {
        addresses,
        asyncQuery: true,
        ignoreCache: ignoreCache ? true : undefined,
        valueThreshold,
      },
      validStatuses: VALID_WITH_PARAMS_SESSION_AND_EXTERNAL_SERVICE,
    });
    return PendingTaskSchema.parse(response);
  };

  const queryXpubBalances = async ({ addresses, blockchain, ignoreCache }: FetchBlockchainBalancePayload): Promise<PendingTask> => {
    const response = await api.get<PendingTask>(`/blockchains/${blockchain}/xpub`, {
      query: {
        asyncQuery: true,
        ignoreCache: ignoreCache ? true : undefined,
        xpub: addresses && addresses.length > 0 ? addresses[0] : undefined,
      },
      validStatuses: VALID_WITH_PARAMS_SESSION_AND_EXTERNAL_SERVICE,
    });
    return PendingTaskSchema.parse(response);
  };

  const fetchDetectedTokensTask = async (chain: string, addresses: string[]): Promise<PendingTask> => {
    const response = await api.post<PendingTask>(
      `/blockchains/${chain}/tokens/detect`,
      {
        addresses,
        asyncQuery: true,
      },
      {
        validStatuses: VALID_WITH_PARAMS_SESSION_AND_EXTERNAL_SERVICE,
      },
    );
    return PendingTaskSchema.parse(response);
  };

  const fetchDetectedTokens = async (chain: string, addresses: string[] | null): Promise<EvmTokensRecord> => {
    const response = await api.post<EvmTokensRecord>(
      `/blockchains/${chain}/tokens/detect`,
      {
        addresses,
        onlyCache: true,
      },
      {
        validStatuses: VALID_WITH_PARAMS_SESSION_AND_EXTERNAL_SERVICE,
      },
    );
    return EvmTokensRecord.parse(response);
  };

  const deleteModuleData = async (module: Nullable<PurgeableModule> = null): Promise<boolean> => {
    const url = module ? `/blockchains/eth/modules/${module}/data` : `/blockchains/eth/modules/data`;
    return api.delete<boolean>(url);
  };

  return {
    deleteModuleData,
    fetchDetectedTokens,
    fetchDetectedTokensTask,
    queryBlockchainBalances,
    queryLoopringBalances,
    queryXpubBalances,
  };
}
