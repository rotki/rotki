import { bigNumberify } from '@rotki/common';
import { runSpecWith } from '@test/utils/mocks/native-task';
import { withSetup } from '@test/utils/with-setup';
import { ok } from 'plainfp/result';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { useSolanaStakeAccounts } from './use-solana-stake-accounts';

const fetchStakeAccounts = vi.hoisted(() => vi.fn<() => Promise<{ taskId: number }>>());

vi.mock('@/modules/staking/api/use-staking-api', () => ({
  useStakingApi: (): { fetchSolanaStakeAccounts: typeof fetchStakeAccounts } => ({ fetchSolanaStakeAccounts: fetchStakeAccounts }),
}));

const { runTask, submitTask } = vi.hoisted(() => ({ runTask: vi.fn(), submitTask: vi.fn() }));

vi.mock('@/modules/task-center/use-native-task', () => ({
  useNativeTask: (): { submitTask: typeof submitTask } => ({ submitTask }),
}));

describe('modules/staking/solana/useSolanaStakeAccounts', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    fetchStakeAccounts.mockResolvedValue({ taskId: 1 });
    submitTask.mockImplementation(runSpecWith(runTask));
  });

  it('should flatten the stake accounts of every owner into rows carrying their owner', async () => {
    runTask.mockResolvedValue(ok({ accounts: {
      ownerA: [{ address: 'stake1', amount: '5', validator: 'vote1' }],
      ownerB: [
        { address: 'stake2', amount: '3', validator: null },
        { address: 'stake3', amount: '2', validator: 'vote1' },
      ],
    }, failed: [] }));
    const { result } = withSetup(() => useSolanaStakeAccounts());

    await result.refresh();

    expect(get(result.rows).map(({ address, owner }) => [address, owner])).toEqual([
      ['stake1', 'ownerA'],
      ['stake2', 'ownerB'],
      ['stake3', 'ownerB'],
    ]);
  });

  it('should keep a stake account that is not delegated without a validator', async () => {
    runTask.mockResolvedValue(ok({ accounts: { ownerA: [{ address: 'stake1', amount: '1', validator: null }] }, failed: [] }));
    const { result } = withSetup(() => useSolanaStakeAccounts());

    await result.refresh();

    expect(get(result.rows)[0].validator).toBeNull();
  });

  it('should total the staked amount across all stake accounts', async () => {
    runTask.mockResolvedValue(ok({ accounts: {
      ownerA: [{ address: 'stake1', amount: '5.5', validator: 'vote1' }],
      ownerB: [{ address: 'stake2', amount: '3', validator: null }],
    }, failed: [] }));
    const { result } = withSetup(() => useSolanaStakeAccounts());

    await result.refresh();

    expect(get(result.total)).toEqual(bigNumberify('8.5'));
  });
});
