import { fetchExternalAsync } from '@/services/utils';
import { api } from '@/services/rotkehlchen-api';
import type { PendingTask } from '@/types/task';

interface UseSushiswapApiReturn {
  fetchSushiswapBalances: () => Promise<PendingTask>;
  fetchSushiswapEvents: () => Promise<PendingTask>;
}

export function useSushiswapApi(): UseSushiswapApiReturn {
  const fetchSushiswapBalances = async (): Promise<PendingTask> => {
    const url = 'blockchains/eth/modules/sushiswap/balances';
    return fetchExternalAsync(api.instance, url);
  };

  const fetchSushiswapEvents = async (): Promise<PendingTask> => {
    const url = 'blockchains/eth/modules/sushiswap/stats';
    return fetchExternalAsync(api.instance, url);
  };

  return {
    fetchSushiswapBalances,
    fetchSushiswapEvents,
  };
}
