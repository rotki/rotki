import { fetchExternalAsync } from '@/services/utils';
import { api } from '@/services/rotkehlchen-api';
import { type PendingTask } from '@/types/task';

export const useUniswapApi = () => {
  const fetchUniswapV2Balances = async (): Promise<PendingTask> => {
    const url = 'blockchains/eth/modules/uniswap/v2/balances';
    return fetchExternalAsync(api.instance, url);
  };

  const fetchUniswapV3Balances = async (): Promise<PendingTask> => {
    const url = 'blockchains/eth/modules/uniswap/v3/balances';
    return fetchExternalAsync(api.instance, url);
  };

  const fetchUniswapEvents = async (): Promise<PendingTask> => {
    const url = 'blockchains/eth/modules/uniswap/history/events';
    return fetchExternalAsync(api.instance, url);
  };

  return {
    fetchUniswapV2Balances,
    fetchUniswapV3Balances,
    fetchUniswapEvents
  };
};
