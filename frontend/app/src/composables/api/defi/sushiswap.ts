import { fetchExternalAsync } from '@/services/utils';
import { api } from '@/services/rotkehlchen-api';
import { type PendingTask } from '@/types/task';

export const useSushiswapApi = () => {
  const fetchSushiswapBalances = (): Promise<PendingTask> => {
    const url = 'blockchains/ETH/modules/sushiswap/balances';
    return fetchExternalAsync(api.instance, url);
  };

  const fetchSushiswapEvents = (): Promise<PendingTask> => {
    const url = 'blockchains/ETH/modules/sushiswap/history/events';
    return fetchExternalAsync(api.instance, url);
  };

  return {
    fetchSushiswapBalances,
    fetchSushiswapEvents
  };
};
