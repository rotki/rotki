import { fetchExternalAsync } from '@/services/utils';
import { api } from '@/services/rotkehlchen-api';
import type { PendingTask } from '@/types/task';

interface UsePoolApiReturn {
  getSushiswapBalances: () => Promise<PendingTask>;
  getUniswapV2Balances: () => Promise<PendingTask>;
}

export function usePoolApi(): UsePoolApiReturn {
  const getUniswapV2Balances = async (): Promise<PendingTask> => {
    const url = 'blockchains/eth/modules/uniswap/v2/balances';
    return fetchExternalAsync(api.instance, url);
  };

  const getSushiswapBalances = async (): Promise<PendingTask> => {
    const url = 'blockchains/eth/modules/sushiswap/balances';
    return fetchExternalAsync(api.instance, url);
  };

  return {
    getSushiswapBalances,
    getUniswapV2Balances,
  };
}
