import { bigNumberify } from '@rotki/common';
import { runSpecWith } from '@test/utils/mocks/native-task';
import { withSetup } from '@test/utils/with-setup';
import { ok } from 'plainfp/result';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { useHyperliquidStaking } from './use-hyperliquid-staking';

const fetchStakingSummaries = vi.hoisted(() => vi.fn<() => Promise<{ taskId: number }>>());

vi.mock('@/modules/staking/api/use-staking-api', () => ({
  useStakingApi: (): { fetchHyperliquidStakingSummaries: typeof fetchStakingSummaries } => ({ fetchHyperliquidStakingSummaries: fetchStakingSummaries }),
}));

function summary(delegated: string, undelegated: string, pendingWithdrawal: string): Record<string, string> {
  return { delegated, pendingWithdrawal, undelegated };
}

const { runTask, submitTask } = vi.hoisted(() => ({ runTask: vi.fn(), submitTask: vi.fn() }));

vi.mock('@/modules/task-center/use-native-task', () => ({
  useNativeTask: (): { submitTask: typeof submitTask } => ({ submitTask }),
}));

describe('modules/staking/hyperliquid/useHyperliquidStaking', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    fetchStakingSummaries.mockResolvedValue({ taskId: 1 });
    submitTask.mockImplementation(runSpecWith(runTask));
  });

  it('should turn each address into a row carrying its address', async () => {
    runTask.mockResolvedValue(ok({ accounts: {
      '0xA': summary('10', '2', '1'),
      '0xB': summary('5', '0', '0'),
    }, failed: [] }));
    const { result } = withSetup(() => useHyperliquidStaking());

    await result.refresh();

    expect(get(result.rows).map(({ address }) => address)).toEqual(['0xA', '0xB']);
  });

  it('should total each state across addresses without mixing them', async () => {
    runTask.mockResolvedValue(ok({ accounts: {
      '0xA': summary('10', '2', '1'),
      '0xB': summary('5', '0.5', '3'),
    }, failed: [] }));
    const { result } = withSetup(() => useHyperliquidStaking());

    await result.refresh();

    expect(get(result.total)).toEqual({
      delegated: bigNumberify('15'),
      pendingWithdrawal: bigNumberify('4'),
      undelegated: bigNumberify('2.5'),
    });
  });
});
