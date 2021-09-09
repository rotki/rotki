import {
  XswapBalance,
  XswapEventDetails,
  XswapPool,
  XswapPoolProfit
} from '@rotki/common/lib/defi/xswap';
import { SushiswapState } from '@/store/defi/sushiswap/types';
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
  balances: (addresses: string[]) => XswapBalance[];
  poolProfit: (addresses: string[]) => XswapPoolProfit[];
  events: (addresses: string[]) => XswapEventDetails[];
  addresses: string[];
  pools: XswapPool[];
}

export const getters: Getters<
  SushiswapState,
  SushiswapGetters,
  RotkehlchenState,
  any
> = {
  balances:
    ({ balances }) =>
    addresses => {
      return getBalances(balances, addresses);
    },
  poolProfit:
    ({ events }) =>
    addresses => {
      return getPoolProfit(events, addresses);
    },
  events:
    ({ events }) =>
    addresses => {
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
