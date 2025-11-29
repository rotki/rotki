import { api } from '@/modules/api/rotki-api';
import { VALID_WITH_SESSION_AND_EXTERNAL_SERVICE } from '@/modules/api/utils';
import { type PendingTask, PendingTaskSchema } from '@/types/task';

interface UsePoolApiReturn {
  getSushiswapBalances: () => Promise<PendingTask>;
  getUniswapV2Balances: () => Promise<PendingTask>;
}

export function usePoolApi(): UsePoolApiReturn {
  const getUniswapV2Balances = async (): Promise<PendingTask> => {
    const response = await api.get<PendingTask>('blockchains/eth/modules/uniswap/v2/balances', {
      query: { asyncQuery: true },
      validStatuses: VALID_WITH_SESSION_AND_EXTERNAL_SERVICE,
    });
    return PendingTaskSchema.parse(response);
  };

  const getSushiswapBalances = async (): Promise<PendingTask> => {
    const response = await api.get<PendingTask>('blockchains/eth/modules/sushiswap/balances', {
      query: { asyncQuery: true },
      validStatuses: VALID_WITH_SESSION_AND_EXTERNAL_SERVICE,
    });
    return PendingTaskSchema.parse(response);
  };

  return {
    getSushiswapBalances,
    getUniswapV2Balances,
  };
}
