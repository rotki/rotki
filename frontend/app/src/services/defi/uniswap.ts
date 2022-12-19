import { type PendingTask } from '@/services/types-api';
import { fetchExternalAsync } from '@/services/utils';
import { api } from '@/services/rotkehlchen-api';

export const useUniswapApi = () => {
  const fetchUniswapV2Balances = async (): Promise<PendingTask> => {
    const url = 'blockchains/ETH/modules/uniswap/v2/balances';
    return fetchExternalAsync(api.instance, url);
  };

  const fetchUniswapV3Balances = async (): Promise<PendingTask> => {
    const url = 'blockchains/ETH/modules/uniswap/v3/balances';
    return fetchExternalAsync(api.instance, url);
  };

  const fetchUniswapEvents = async (): Promise<PendingTask> => {
    const url = 'blockchains/ETH/modules/uniswap/history/events';
    return fetchExternalAsync(api.instance, url);
  };

  return {
    fetchUniswapV2Balances,
    fetchUniswapV3Balances,
    fetchUniswapEvents
  };
};
