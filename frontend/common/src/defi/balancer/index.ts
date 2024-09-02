import { z } from 'zod';
import { Balance } from '../../balances';
import { type BigNumber, NumericString } from '../../numbers';
import type { XswapPool } from '../xswap';

const BalancerUnderlyingToken = z.object({
  token: z.string(),
  totalAmount: NumericString,
  userBalance: Balance,
  usdPrice: NumericString,
  weight: z.string(),
});

export type BalancerUnderlyingToken = z.infer<typeof BalancerUnderlyingToken>;

const BalancerBalance = z.object({
  address: z.string(),
  tokens: z.array(BalancerUnderlyingToken),
  totalAmount: NumericString,
  userBalance: Balance,
});

export type BalancerBalance = z.infer<typeof BalancerBalance>;

export const BalancerBalances = z.record(z.array(BalancerBalance));

export type BalancerBalances = z.infer<typeof BalancerBalances>;

const PoolAmounts = z.record(NumericString);

export type PoolAmounts = z.infer<typeof PoolAmounts>;

export interface BalancerProfitLoss {
  readonly pool: XswapPool;
  readonly tokens: string[];
  readonly usdProfitLoss: BigNumber;
  readonly profitLossAmount: PoolAmounts;
}
