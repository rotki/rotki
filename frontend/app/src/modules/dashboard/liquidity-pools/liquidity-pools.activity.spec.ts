import { describe, expect, it } from 'vitest';
import { ActivityPart } from '@/modules/task-center/core/types';
import { liquidityPoolsActivity } from './liquidity-pools.activity';

describe('liquidity pool activity ids', () => {
  it('should key each protocol\'s pools by the protocol', () => {
    expect(liquidityPoolsActivity.id({ part: ActivityPart.UNISWAP_V2 })).toBe('liquidity-pools:uniswap-v2');
    expect(liquidityPoolsActivity.id({ part: ActivityPart.SUSHISWAP })).toBe('liquidity-pools:sushiswap');
  });
});
