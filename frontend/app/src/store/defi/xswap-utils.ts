import { UniswapBalances } from '@/services/defi/types/uniswap';
import {
  UniswapBalance,
  UniswapEventDetails,
  UniswapEvents,
  UniswapPool,
  UniswapPoolProfit
} from '@/store/defi/types';
import { Writeable } from '@/types';

export function getPools(
  balances: UniswapBalances,
  events: UniswapEvents
): UniswapPool[] {
  const pools: UniswapPool[] = [];
  const known: { [address: string]: boolean } = {};
  for (const account in balances) {
    const accountBalances = balances[account];
    if (!accountBalances || accountBalances.length === 0) {
      continue;
    }
    for (const { assets, address } of accountBalances) {
      if (known[address]) {
        continue;
      }
      known[address] = true;
      pools.push({
        address,
        assets: assets.map(({ asset }) => asset)
      });
    }
  }

  for (const address in events) {
    const details = events[address];
    for (const { poolAddress, token0, token1 } of details) {
      if (known[poolAddress]) {
        continue;
      }
      known[poolAddress] = true;
      pools.push({
        address: poolAddress,
        assets: [token0, token1]
      });
    }
  }
  return pools;
}

export function getEventDetails(
  events: UniswapEvents,
  addresses: string[]
): UniswapEventDetails[] {
  const eventDetails: UniswapEventDetails[] = [];
  for (const address in events) {
    if (addresses.length > 0 && !addresses.includes(address)) {
      continue;
    }
    const details = events[address];
    for (const { events, poolAddress, token0, token1 } of details) {
      for (const event of events) {
        eventDetails.push({
          ...event,
          address,
          poolAddress: poolAddress,
          token0: token0,
          token1: token1
        });
      }
    }
  }
  return eventDetails;
}

export function getPoolProfit(
  events: UniswapEvents,
  addresses: string[]
): UniswapPoolProfit[] {
  const perPoolProfit: {
    [poolAddress: string]: Writeable<UniswapPoolProfit>;
  } = {};
  for (const address in events) {
    if (addresses.length > 0 && !addresses.includes(address)) {
      continue;
    }

    const details = events[address];
    for (const detail of details) {
      const { poolAddress } = detail;
      const profit = perPoolProfit[poolAddress];
      if (profit) {
        perPoolProfit[poolAddress] = {
          ...profit,
          profitLoss0: profit.profitLoss0.plus(detail.profitLoss0),
          profitLoss1: profit.profitLoss1.plus(detail.profitLoss1),
          usdProfitLoss: profit.usdProfitLoss.plus(detail.usdProfitLoss)
        };
      } else {
        const { events: _, address, ...poolProfit } = detail;
        perPoolProfit[poolAddress] = poolProfit;
      }
    }
  }
  return Object.values(perPoolProfit);
}

export function getBalances(
  xswapBalance: UniswapBalances,
  addresses: string[]
): UniswapBalance[] {
  const balances: { [poolAddress: string]: Writeable<UniswapBalance> } = {};
  for (const account in xswapBalance) {
    if (addresses.length > 0 && !addresses.includes(account)) {
      continue;
    }
    const accountBalances = xswapBalance[account];
    if (!accountBalances || accountBalances.length === 0) {
      continue;
    }
    for (const {
      userBalance,
      totalSupply,
      assets,
      address
    } of accountBalances) {
      const balance = balances[address];
      if (balance) {
        const oldBalance = balance.userBalance;
        balance.userBalance = {
          amount: oldBalance.amount.plus(userBalance.amount),
          usdValue: oldBalance.usdValue.plus(userBalance.usdValue)
        };

        if (balance.totalSupply !== null && totalSupply !== null) {
          balance.totalSupply = balance.totalSupply.plus(totalSupply);
        }
      } else {
        balances[address] = {
          account,
          userBalance,
          totalSupply,
          assets,
          poolAddress: address
        };
      }
    }
  }
  return Object.values(balances);
}
