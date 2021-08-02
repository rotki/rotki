import { SushiswapState } from '@/store/defi/sushiswap/types';
import {
  UniswapBalance,
  UniswapEventDetails,
  UniswapPool,
  UniswapPoolProfit
} from '@/store/defi/types';
import {
  getBalances,
  getEventDetails,
  getPoolProfit,
  getPools
} from '@/store/defi/xswap-utils';
import { RotkehlchenState } from '@/store/types';
import { Getters } from '@/store/typing';
import { uniqueStrings } from '@/utils/data';

interface SushiswapGetters {
  balances: (addresses: string[]) => UniswapBalance[];
  poolProfit: (addresses: string[]) => UniswapPoolProfit[];
  events: (addresses: string[]) => UniswapEventDetails[];
  addresses: string[];
  pools: UniswapPool[];
}

export const getters: Getters<
  SushiswapState,
  SushiswapGetters,
  RotkehlchenState,
  any
> = {
  balances: ({ balances }) => addresses => {
    return getBalances(balances, addresses);
  },
  poolProfit: ({ events }) => addresses => {
    return getPoolProfit(events, addresses);
  },
  events: ({ events }) => addresses => {
    return getEventDetails(events, addresses);
  },
  addresses: ({ events, balances }) => {
    return Object.keys(balances)
      .concat(Object.keys(events))
      .filter(uniqueStrings);
  },
  pools: ({ balances, events }) => {
    return getPools(balances, events);
  }
};
