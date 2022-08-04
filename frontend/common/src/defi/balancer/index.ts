import {default as BigNumber} from "bignumber.js";
import {z} from "zod";
import {Balance, NumericString} from "../../index";


const BalancerUnderlyingToken = z.object({
  token: z.string(),
  totalAmount: NumericString,
  userBalance: Balance,
  usdPrice: NumericString,
  weight: z.string()
})

export type BalancerUnderlyingToken =z.infer<typeof BalancerUnderlyingToken>

const BalancerBalance = z.object({
  address: z.string(),
  tokens: z.array(BalancerUnderlyingToken),
  totalAmount: NumericString,
  userBalance: Balance
})

type BalancerBalance = z.infer<typeof BalancerBalance>

export interface BalancerBalanceWithOwner extends BalancerBalance {
  readonly owner: string;
}

export const BalancerBalances = z.record(z.array(BalancerBalance))
export type BalancerBalances = z.infer<typeof BalancerBalances>

const PoolToken = z.object({
  token: z.string(),
  weight: z.string()
})

const PoolAmounts = z.record(NumericString)

export type PoolAmounts = z.infer<typeof PoolAmounts>

const Pool = z.object({
  name: z.string(),
  address: z.string()
})

export type Pool = z.infer<typeof Pool>

const BalancerEvent =z.object({
  txHash: z.string(),
  logIndex: z.number(),
  timestamp: z.number(),
  eventType: z.enum(['mint', 'burn']),
  lpBalance: Balance,
  amounts: PoolAmounts,
  pool: Pool.optional()
})

export type BalancerEvent = z.infer<typeof BalancerEvent>

const BalancerPoolDetails = z.object({
  poolAddress: z.string(),
  poolTokens: z.array(PoolToken),
  events: z.array(BalancerEvent),
  profitLossAmounts: PoolAmounts,
  usdProfitLoss: NumericString
})

export const BalancerEvents = z.record(z.array(BalancerPoolDetails))
export type BalancerEvents = z.infer<typeof BalancerEvents>

export interface BalancerProfitLoss {
  readonly pool: Pool;
  readonly tokens: string[];
  readonly usdProfitLoss: BigNumber;
  readonly profitLossAmount: PoolAmounts;
}
