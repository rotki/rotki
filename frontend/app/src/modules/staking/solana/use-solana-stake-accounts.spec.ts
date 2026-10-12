import type { SolanaStakeAccounts } from '@/modules/staking/staking-types';
import { bigNumberify } from '@rotki/common';
import { withSetup } from '@test/utils/with-setup';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { useSolanaStakeAccounts } from './use-solana-stake-accounts';

const fetchStakeAccounts = vi.hoisted(() => vi.fn<() => Promise<SolanaStakeAccounts>>());

vi.mock('@/modules/staking/api/use-staking-api', () => ({
  useStakingApi: (): { fetchSolanaStakeAccounts: typeof fetchStakeAccounts } => ({ fetchSolanaStakeAccounts: fetchStakeAccounts }),
}));

describe('modules/staking/solana/useSolanaStakeAccounts', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('should flatten the stake accounts of every owner into rows carrying their owner', async () => {
    fetchStakeAccounts.mockResolvedValue({
      ownerA: [{ address: 'stake1', amount: bigNumberify(5), validator: 'vote1' }],
      ownerB: [
        { address: 'stake2', amount: bigNumberify(3), validator: null },
        { address: 'stake3', amount: bigNumberify(2), validator: 'vote1' },
      ],
    });
    const { result } = withSetup(() => useSolanaStakeAccounts());

    await result.refresh();

    expect(get(result.rows).map(({ address, owner }) => [address, owner])).toEqual([
      ['stake1', 'ownerA'],
      ['stake2', 'ownerB'],
      ['stake3', 'ownerB'],
    ]);
  });

  it('should total the staked amount across all stake accounts', async () => {
    fetchStakeAccounts.mockResolvedValue({
      ownerA: [{ address: 'stake1', amount: bigNumberify('5.5'), validator: 'vote1' }],
      ownerB: [{ address: 'stake2', amount: bigNumberify('3'), validator: null }],
    });
    const { result } = withSetup(() => useSolanaStakeAccounts());

    await result.refresh();

    expect(get(result.total)).toEqual(bigNumberify('8.5'));
  });
});
