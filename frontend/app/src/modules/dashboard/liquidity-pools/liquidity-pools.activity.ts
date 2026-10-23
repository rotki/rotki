import { defineActivity } from '@/modules/task-center/core/activity-descriptor';
import { ActivityKind, type ActivityPart } from '@/modules/task-center/core/types';

/** The protocols whose pool balances load through `usePoolDataFetching`. */
export type LiquidityPoolsPart = typeof ActivityPart.SUSHISWAP | typeof ActivityPart.UNISWAP_V2;

/** One protocol's pool balances, a singleton per protocol. */
export const liquidityPoolsActivity = defineActivity<{ part: LiquidityPoolsPart }, readonly [LiquidityPoolsPart]>({
  key: subject => [subject.part],
  kind: ActivityKind.LIQUIDITY_POOLS,
});
