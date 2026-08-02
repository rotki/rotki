import { beforeEach, describe, expect, it, vi } from 'vitest';
import { nextTick } from 'vue';
import { type Activity, ActivityKind, ActivityStatus, makeActivityId } from '@/modules/task-center/core/types';
import '@test/i18n';

const activities = ref<Activity[]>([]);
const blockchainStatus = ref<{ active: boolean }>({ active: false });
const tokenStatus = ref<{ active: boolean }>({ active: false });

vi.mock('@/modules/task-center/use-task-orchestrator', () => ({
  useTaskOrchestrator: vi.fn().mockReturnValue({ activities }),
}));

vi.mock('@/modules/task-center/use-task-center', () => ({
  useTaskCenter: vi.fn().mockReturnValue({
    useIsActive: vi.fn().mockImplementation((kind: string) => computed<boolean>(() =>
      get(kind === ActivityKind.BLOCKCHAIN_BALANCES ? blockchainStatus : tokenStatus).active,
    )),
    useWorkStatus: vi.fn().mockImplementation((kind: string) =>
      kind === ActivityKind.BLOCKCHAIN_BALANCES ? blockchainStatus : tokenStatus,
    ),
  }),
}));

vi.mock('@/modules/core/common/use-supported-chains', () => ({
  useSupportedChains: vi.fn().mockReturnValue({
    getChainName: (chain: string): string => chain,
  }),
}));

function balanceActivity(chain: string, status: ActivityStatus): Activity {
  return {
    cancellable: true,
    id: makeActivityId(ActivityKind.BLOCKCHAIN_BALANCES, chain),
    kind: ActivityKind.BLOCKCHAIN_BALANCES,
    percentage: -1,
    rerunnable: true,
    source: { type: 'native' },
    status,
    title: 'Blockchain balances',
  };
}

async function load(): Promise<typeof import('./use-balance-query-progress')> {
  vi.resetModules();
  return import('./use-balance-query-progress');
}

describe('useBalanceQueryProgress', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    set(activities, []);
    set(blockchainStatus, { active: false });
    set(tokenStatus, { active: false });
  });

  it('should report isBalanceQuerying from the work status', async () => {
    const { useBalanceQueryProgress } = await load();
    const { isBalanceQuerying } = useBalanceQueryProgress();

    expect(get(isBalanceQuerying)).toBe(false);
    set(blockchainStatus, { active: true });
    expect(get(isBalanceQuerying)).toBe(true);
  });

  it('should be undefined when no balance activities exist', async () => {
    const { useBalanceQueryProgress } = await load();
    const { balanceProgress } = useBalanceQueryProgress();
    await nextTick();

    expect(get(balanceProgress)).toBeUndefined();
  });

  it('should build per-batch progress from the running and pending activities', async () => {
    set(activities, [
      balanceActivity('eth', ActivityStatus.RUNNING),
      balanceActivity('optimism', ActivityStatus.PENDING),
    ]);

    const { useBalanceQueryProgress } = await load();
    const { balanceProgress } = useBalanceQueryProgress();
    await nextTick();

    const progress = get(balanceProgress);
    expect(progress?.totalSteps).toBe(2);
    expect(progress?.currentStep).toBe(1);
    expect(progress?.percentage).toBe(0);
    expect(progress?.currentOperationData?.type).toBe(ActivityKind.BLOCKCHAIN_BALANCES);
    expect(progress?.currentOperationData?.chain).toBe('eth');
  });

  it('should count terminal members toward completed without dropping the batch total', async () => {
    set(activities, [
      balanceActivity('eth', ActivityStatus.RUNNING),
      balanceActivity('optimism', ActivityStatus.PENDING),
    ]);

    const { useBalanceQueryProgress } = await load();
    const { balanceProgress } = useBalanceQueryProgress();
    await nextTick();

    // eth completes, optimism starts running
    set(activities, [
      balanceActivity('eth', ActivityStatus.COMPLETE),
      balanceActivity('optimism', ActivityStatus.RUNNING),
    ]);
    await nextTick();

    const progress = get(balanceProgress);
    expect(progress?.totalSteps).toBe(2);
    expect(progress?.currentStep).toBe(2);
    expect(progress?.percentage).toBe(50);
    expect(progress?.currentOperationData?.chain).toBe('optimism');
  });
});
