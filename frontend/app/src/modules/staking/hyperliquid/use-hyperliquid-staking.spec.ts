import type { HyperliquidStakingSummaries } from '@/modules/staking/staking-types';
import { bigNumberify } from '@rotki/common';
import { withSetup } from '@test/utils/with-setup';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { useHyperliquidStaking } from './use-hyperliquid-staking';

const fetchStakingSummaries = vi.hoisted(() => vi.fn<() => Promise<HyperliquidStakingSummaries>>());

vi.mock('@/modules/staking/api/use-staking-api', () => ({
  useStakingApi: (): { fetchHyperliquidStakingSummaries: typeof fetchStakingSummaries } => ({ fetchHyperliquidStakingSummaries: fetchStakingSummaries }),
}));

function summary(delegated: string, undelegated: string, pendingWithdrawal: string): HyperliquidStakingSummaries[string] {
  return {
    delegated: bigNumberify(delegated),
    pendingWithdrawal: bigNumberify(pendingWithdrawal),
    undelegated: bigNumberify(undelegated),
  };
}

describe('modules/staking/hyperliquid/useHyperliquidStaking', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('should turn each address into a row carrying its address', async () => {
    fetchStakingSummaries.mockResolvedValue({
      '0xA': summary('10', '2', '1'),
      '0xB': summary('5', '0', '0'),
    });
    const { result } = withSetup(() => useHyperliquidStaking());

    await result.refresh();

    expect(get(result.rows).map(({ address }) => address)).toEqual(['0xA', '0xB']);
  });

  it('should total each state across addresses without mixing them', async () => {
    fetchStakingSummaries.mockResolvedValue({
      '0xA': summary('10', '2', '1'),
      '0xB': summary('5', '0.5', '3'),
    });
    const { result } = withSetup(() => useHyperliquidStaking());

    await result.refresh();

    expect(get(result.total)).toEqual({
      delegated: bigNumberify('15'),
      pendingWithdrawal: bigNumberify('4'),
      undelegated: bigNumberify('2.5'),
    });
  });
});
