import { fetchExternalAsync } from '@/services/utils';
import { api } from '@/services/rotkehlchen-api';
import type { PendingTask } from '@/types/task';

interface UseUniswapApiReturn {
  fetchUniswapV2Balances: () => Promise<PendingTask>;
  fetchUniswapV3Balances: () => Promise<PendingTask>;
  fetchUniswapEvents: () => Promise<PendingTask>;
}

export function useUniswapApi(): UseUniswapApiReturn {
  const fetchUniswapV2Balances = (): Promise<PendingTask> => {
    const url = 'blockchains/eth/modules/uniswap/v2/balances';
    return fetchExternalAsync(api.instance, url);
  };

  const fetchUniswapV3Balances = (): Promise<PendingTask> => {
    const url = 'blockchains/eth/modules/uniswap/v3/balances';
    return fetchExternalAsync(api.instance, url);
  };

  const fetchUniswapEvents = (): Promise<PendingTask> => {
    const url = 'blockchains/eth/modules/uniswap/stats';
    return fetchExternalAsync(api.instance, url);
  };

  return {
    fetchUniswapV2Balances,
    fetchUniswapV3Balances,
    fetchUniswapEvents,
  };
}
